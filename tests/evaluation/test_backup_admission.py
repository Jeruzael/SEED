"""R3: full temporary backup allocation is admitted before destination creation."""
from types import SimpleNamespace
import sqlite3
import pytest
from .test_storage_identity import assigned


def fixture(foundation_module, tmp_path):
    root,cap,path=assigned(foundation_module,tmp_path)
    a=foundation_module('db_adapter'); s=foundation_module('state')
    monitor=a.GrowthMonitor(cap.home)
    db=a.OwnedSqlite(cap,monitor).connect(path)
    return root,s.OwnedState(cap,SimpleNamespace(db=db),monitor),a


@pytest.mark.parametrize('operation',['checkpoint','clone'])
def test_backup_rejects_combined_workspace_before_creation(foundation_module,tmp_path,monkeypatch,operation):
    root,state,a=fixture(foundation_module,tmp_path)
    slot=root.assign_learner('run',1)
    monkeypatch.setattr(foundation_module('state'),'_worker_only',lambda:None)
    used=sum(p.stat().st_size for p in state.capability.home.parent.rglob('*') if p.is_file())
    state.monitor.workspace_limit=used+8191
    target=state.capability.home/'checkpoint.sqlite3' if operation=='checkpoint' else slot.home/'memory.sqlite3'
    try:
        with pytest.raises(a.LimitReached):
            state.checkpoint() if operation=='checkpoint' else state.clone(slot)
        assert not target.exists()
        assert state.monitor.stopped
    finally: state.memory.db.close()


@pytest.mark.parametrize('delta',[0,-1])
def test_backup_exact_reserved_boundary(foundation_module,tmp_path,delta):
    _,state,a=fixture(foundation_module,tmp_path)
    # 8192-byte DB + one complete journal page set + bounded 64-KiB metadata margin.
    used=sum(p.stat().st_size for p in state.capability.home.parent.rglob('*') if p.is_file())
    state.monitor.workspace_limit=used+2*8192+65536+delta
    try:
        if delta:
            with pytest.raises(a.LimitReached): state.checkpoint()
            assert not (state.capability.home/'checkpoint.sqlite3').exists()
        else:
            path=state.checkpoint()
            with sqlite3.connect(path) as db: assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    finally: state.memory.db.close()


def test_other_retained_snapshots_charged(foundation_module,tmp_path):
    _,state,a=fixture(foundation_module,tmp_path)
    (state.capability.home.parent/'variant-c-1.sqlite3').write_bytes(bytes(32768))
    state.monitor.workspace_limit=32768
    try:
        with pytest.raises(a.LimitReached): state.checkpoint()
        assert not (state.capability.home/'checkpoint.sqlite3').exists()
    finally: state.memory.db.close()


def test_failed_backup_retains_only_incomplete_prefix(foundation_module,tmp_path,monkeypatch):
    _,state,a=fixture(foundation_module,tmp_path)
    def failed(target,**kwargs):
        target.execute('CREATE TABLE partial(x)'); target.commit()
        raise RuntimeError('technical injected backup failure')
    monkeypatch.setattr(state.memory.db,'backup',failed)
    try:
        with pytest.raises(RuntimeError): state.checkpoint()
        assert state.monitor.stopped
        target=state.capability.home/'checkpoint.sqlite3'
        assert target.exists() and target.stat().st_size==8192
        with pytest.raises(a.LimitReached): state.checkpoint()
    finally: state.memory.db.close()
