"""R1: observable admission/identity failures are terminal, not race prevention."""
from dataclasses import replace
import os
import sqlite3
import pytest
from types import SimpleNamespace


def assigned(foundation_module, tmp_path):
    root = foundation_module('paths').EvaluationRoot.create(tmp_path.resolve())
    cap = root.assign_learner('run', 0)
    path = cap.home / 'memory.sqlite3'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE t(x)')
    return root, cap, path


def test_missing_existing_database_never_created(foundation_module, tmp_path):
    _, cap, path = assigned(foundation_module, tmp_path)
    path.unlink()
    a = foundation_module('db_adapter')
    with pytest.raises((ValueError, sqlite3.DatabaseError)):
        a.OwnedSqlite(cap, a.GrowthMonitor(cap.home)).connect(path)
    assert not path.exists()


def test_post_connect_observable_replacement_is_terminal(foundation_module, tmp_path, monkeypatch):
    _, cap, path = assigned(foundation_module, tmp_path)
    a = foundation_module('db_adapter')
    real = a.CONNECT
    def changed(*args, **kwargs):
        db = real(*args, **kwargs)
        path.rename(path.with_name('old.sqlite3'))
        with real(path) as replacement:
            replacement.execute('CREATE TABLE foreign_data(x)')
        return db
    monkeypatch.setattr(a, 'CONNECT', changed)
    with pytest.raises(ValueError):
        a.OwnedSqlite(cap, a.GrowthMonitor(cap.home)).connect(path)


@pytest.mark.parametrize('unsafe', ['symlink', 'fifo', 'hardlink'])
def test_preexisting_unsafe_database_rejected(foundation_module, tmp_path, unsafe):
    _, cap, path = assigned(foundation_module, tmp_path)
    path.unlink()
    foreign = tmp_path / 'foreign.sqlite3'
    foreign.write_bytes(b'foreign')
    if unsafe == 'symlink': path.symlink_to(foreign)
    elif unsafe == 'fifo': os.mkfifo(path)
    else: os.link(foreign, path)
    a = foundation_module('db_adapter')
    with pytest.raises(ValueError):
        a.OwnedSqlite(cap, a.GrowthMonitor(cap.home)).connect(path)
    assert foreign.read_bytes() == b'foreign'


@pytest.mark.parametrize('suffix', ['-wal', '-shm', '-journal'])
def test_unsafe_sidecar_during_operation_is_terminal(foundation_module, tmp_path, suffix):
    _, cap, path = assigned(foundation_module, tmp_path)
    a = foundation_module('db_adapter')
    db = a.OwnedSqlite(cap, a.GrowthMonitor(cap.home)).connect(path)
    sidecar = path.with_name(path.name + suffix)
    sidecar.symlink_to(tmp_path / 'private')
    try:
        with pytest.raises(ValueError): db.execute('SELECT * FROM t')
        sidecar.unlink()
        with pytest.raises(ValueError): db.execute('SELECT * FROM t')
    finally: db.close()


def test_second_trusted_writer_rejected_and_release(foundation_module, tmp_path):
    _, cap, path = assigned(foundation_module, tmp_path)
    a = foundation_module('db_adapter')
    factory = a.OwnedSqlite(cap, a.GrowthMonitor(cap.home))
    first = factory.connect(path)
    try:
        with pytest.raises(ValueError): factory.connect(path)
    finally: first.close()
    factory.connect(path).close()


def test_foreign_root_capability_routing_rejected(foundation_module, tmp_path, monkeypatch):
    _, cap, path = assigned(foundation_module, tmp_path)
    a = foundation_module('db_adapter')
    monkeypatch.setenv('SEED_HOME', str(tmp_path / 'installed'))
    foreign = tmp_path / 'foreign'
    foreign.mkdir()
    (foreign / '.ownership').write_text(cap.token)
    st = foreign.stat()
    forged = replace(cap, home=foreign, inode=(st.st_dev, st.st_ino))
    with pytest.raises(ValueError): forged.validate()
    with pytest.raises(ValueError):
        a.OwnedSqlite(cap, a.GrowthMonitor(cap.home)).connect(foreign / 'memory.sqlite3')
    assert not (tmp_path / 'installed').exists()


@pytest.mark.parametrize('operation', ['checkpoint','clone'])
def test_invalidated_source_not_published(foundation_module, tmp_path, monkeypatch, operation):
    root, cap, path = assigned(foundation_module, tmp_path)
    a = foundation_module('db_adapter')
    s = foundation_module('state')
    db = a.OwnedSqlite(cap, a.GrowthMonitor(cap.home)).connect(path)
    state = s.OwnedState(cap, SimpleNamespace(db=db), db.monitor)
    slot = root.assign_learner('run', 1)
    monkeypatch.setattr(s, '_worker_only', lambda: None)
    path.rename(path.with_name('old.sqlite3'))
    with sqlite3.connect(path) as replacement: replacement.execute('CREATE TABLE replacement(x)')
    try:
        with pytest.raises(ValueError):
            state.checkpoint() if operation=='checkpoint' else state.clone(slot)
        assert not (cap.home/'checkpoint.sqlite3').exists()
        assert not (slot.home/'memory.sqlite3').exists()
    finally: db.close()


def test_invalidated_checkpoint_target_not_published(foundation_module, tmp_path, monkeypatch):
    _, cap, path = assigned(foundation_module, tmp_path)
    a = foundation_module('db_adapter')
    s = foundation_module('state')
    db = a.OwnedSqlite(cap, a.GrowthMonitor(cap.home)).connect(path)
    state = s.OwnedState(cap, SimpleNamespace(db=db), db.monitor)
    real = s.CONNECT
    target = cap.home/'checkpoint.sqlite3'
    def changed(*args, **kwargs):
        connection = real(*args, **kwargs)
        target.rename(target.with_name('old-checkpoint.sqlite3'))
        target.write_bytes(b'foreign')
        return connection
    monkeypatch.setattr(s, 'CONNECT', changed)
    try:
        with pytest.raises(ValueError): state.checkpoint()
    finally: db.close()


@pytest.mark.parametrize('suffix',['','-wal','-shm','-journal'])
def test_observable_foreign_owner_rejected(foundation_module,tmp_path,monkeypatch,suffix):
    _,cap,path=assigned(foundation_module,tmp_path)
    a=foundation_module('db_adapter')
    from pathlib import Path
    target=Path(str(path)+suffix)
    if suffix: target.write_bytes(b'fixture')
    real=Path.lstat
    def owner_changed(value,*args,**kwargs):
        st=real(value,*args,**kwargs)
        if value==target:
            return SimpleNamespace(st_mode=st.st_mode,st_uid=os.geteuid()+1,st_nlink=st.st_nlink,st_dev=st.st_dev,st_ino=st.st_ino)
        return st
    monkeypatch.setattr(Path,'lstat',owner_changed)
    reached=[]
    monkeypatch.setattr(a,'CONNECT',lambda *args,**kwargs: reached.append(True))
    with pytest.raises(ValueError): a.OwnedSqlite(cap,a.GrowthMonitor(cap.home)).connect(path)
    assert reached==[]


def test_preconnect_mismatch_latches_run_terminal(foundation_module,tmp_path):
    _,cap,path=assigned(foundation_module,tmp_path)
    a=foundation_module('db_adapter'); monitor=a.GrowthMonitor(cap.home)
    factory=a.OwnedSqlite(cap,monitor)
    sidecar=path.with_name(path.name+'-wal'); sidecar.symlink_to(tmp_path/'foreign')
    with pytest.raises(ValueError): factory.connect(path)
    assert monitor.stopped
    sidecar.unlink()
    with pytest.raises(ValueError): factory.connect(path)
