"""External transaction guard; original producer SQL and schema are unchanged."""
import os
from pathlib import Path
import sqlite3
import stat
import fcntl
import weakref
from .contracts import ContractError
from .paths import _directory, _open_file

CONNECT = sqlite3.connect


class StorageIdentity:
    """Observable trusted-code checks; not hostile native-open race prevention."""
    def __init__(self, capability, name='memory.sqlite3', *, writer=True):
        self.capability, self.path = capability, capability.home/name
        self.failed, self.fd, self.lease = False, None, None
        capability.validate()
        kind, identity = ('state','db') if name=='memory.sqlite3' else ('snapshot','checkpoint')
        self.fd = capability.open(kind,identity,'read')
        st = os.fstat(self.fd)
        self.inode = (st.st_dev,st.st_ino)
        try:
            if writer:
                # SQLite owns locks on the DB; use a distinct owned lease file.
                lease_name='writer' if name=='memory.sqlite3' else 'checkpoint'
                try:
                    lease=capability.open('lease',lease_name,'create')
                    os.close(lease)
                except ContractError:
                    pass
                self.lease=capability.open('lease',lease_name,'read')
                fcntl.flock(self.lease,fcntl.LOCK_EX|fcntl.LOCK_NB)
            self.validate()
        except BaseException:
            self.close()
            raise ContractError() from None

    def validate(self, connection=None):
        if self.failed:
            raise ContractError()
        try:
            self.capability.validate()
            for suffix in ('','-wal','-shm','-journal'):
                file=Path(str(self.path)+suffix)
                if suffix and not file.exists() and not file.is_symlink():
                    continue
                st=file.lstat()
                if not stat.S_ISREG(st.st_mode) or st.st_uid!=os.geteuid() or st.st_nlink!=1:
                    raise ContractError()
                if not suffix and (st.st_dev,st.st_ino)!=self.inode:
                    raise ContractError()
            if connection is not None:
                facts=connection.execute('PRAGMA database_list').fetchall()
                main=[row for row in facts if row[1]=='main']
                if len(main)!=1 or main[0][2]!=str(self.path) or any(row[1]!='main' and (row[1]!='temp' or row[2]!='') for row in facts):
                    raise ContractError()
        except (OSError,ValueError,sqlite3.DatabaseError):
            self.failed=True
            raise ContractError() from None

    def close(self):
        if self.fd is not None:
            os.close(self.fd)
            self.fd=None
        if self.lease is not None:
            os.close(self.lease)
            self.lease=None


class LimitReached(RuntimeError):
    def __init__(self):
        super().__init__('LIMIT_REACHED')


class RunBudget:
    """Durable run-scoped terminal latch; never cleared by a new monitor/spawn."""
    def __init__(self, run):
        self.run=Path(run)

    @property
    def stopped(self):
        directory=_directory(self.run)
        try:
            try: os.stat('.budget-terminal',dir_fd=directory,follow_symlinks=False)
            except FileNotFoundError: return False
            fd=_open_file(directory,'.budget-terminal','read')
            with os.fdopen(fd,'rb') as f:
                if f.read(64)!=b'B10_RUN_TERMINAL_V1':
                    raise ContractError()
            return True
        finally: os.close(directory)

    def stop(self):
        directory=_directory(self.run)
        try:
            try: fd=_open_file(directory,'.budget-terminal','create')
            except ContractError:
                if not self.stopped: raise
                return
            with os.fdopen(fd,'wb') as f:
                f.write(b'B10_RUN_TERMINAL_V1'); f.flush(); os.fsync(f.fileno())
            os.fsync(directory)
        finally: os.close(directory)


class GrowthMonitor:
    def __init__(self, home, *, logical_limit=32*1024**2, physical_limit=64*1024**2, workspace_limit=128*1024**2):
        self.home = Path(home)
        self.logical_limit, self.physical_limit, self.workspace_limit = logical_limit, physical_limit, workspace_limit
        self.run_budget=RunBudget(self.home.parent)
        self._stopped, self.overshoot_exceeded = False, False
        self.invalid_storage=False
        self.commits = 0

    @property
    def stopped(self): return self._stopped or self.run_budget.stopped
    @stopped.setter
    def stopped(self,value):
        if value:
            self._stopped=True
            self.run_budget.stop()

    def check(self, connection):
        self.commits += 1
        logical = connection.execute('PRAGMA page_count').fetchone()[0] * connection.execute('PRAGMA page_size').fetchone()[0]
        physical = sum(p.stat().st_size for p in self.home.iterdir() if p.name in ('memory.sqlite3','memory.sqlite3-wal','memory.sqlite3-shm') and p.is_file())
        workspace = self.workspace_bytes()
        if logical > self.logical_limit or physical > self.physical_limit or workspace > self.workspace_limit:
            self.stopped = True
            self.overshoot_exceeded = physical > self.physical_limit+36*1024**2 or workspace > self.workspace_limit+36*1024**2
            raise LimitReached()

    def workspace_bytes(self):
        workspace = 0
        for p in self.home.parent.rglob('*'):
            st = p.lstat()
            if stat.S_ISREG(st.st_mode):
                if st.st_nlink != 1 or st.st_uid != os.geteuid():
                    self.stopped = True
                    raise ContractError()
                workspace += st.st_size
            elif not stat.S_ISDIR(st.st_mode):
                self.stopped = True
                raise ContractError()
        return workspace

    def admit_backup(self, connection):
        if self.stopped:
            raise LimitReached()
        logical=connection.execute('PRAGMA page_count').fetchone()[0]*connection.execute('PRAGMA page_size').fetchone()[0]
        # Destination plus a full rollback journal page set and bounded metadata.
        allocation=2*logical+65536
        if logical>self.logical_limit or self.workspace_bytes()+allocation>self.workspace_limit:
            self.stopped=True
            raise LimitReached()
        return logical

    def check_backup(self, target, logical):
        if target.stat().st_size>logical or self.workspace_bytes()>self.workspace_limit:
            self.stopped=True
            raise LimitReached()


def _read_only(sql):
    first = sql.lstrip().split(None,1)[0].upper() if sql.strip() else ''
    if first in ('SELECT','EXPLAIN'):
        return True
    if first == 'PRAGMA':
        text = sql.lower().strip().rstrip(';')
        return '=' not in text and any(text.startswith('pragma '+x) for x in ('page_count','page_size','table_info','index_list','index_info','foreign_key_list','integrity_check','compile_options'))
    return False


class CursorProxy:
    def __init__(self, connection, cursor, *, mutating=False):
        self.connection, self._cursor = connection, cursor
        self._mutating,self._closed=mutating,False
        connection._cursors.add(self)
    def execute(self, sql, parameters=()):
        if self._mutating:
            self.close()
            self._cursor=self.connection._connection.cursor()
            self._closed=False
        self.connection._execute(self._cursor.execute,sql,parameters)
        self._mutating=not _read_only(sql)
        return self
    def executemany(self, sql, parameters):
        # Individual executions also cover autocommit producers.
        for row in parameters:
            self.execute(sql,row)
        return self
    def __iter__(self):
        return self
    def __next__(self):
        value=self.fetchone()
        if value is None:
            raise StopIteration
        return value
    def _finish(self, method, *args):
        self.connection.validate_storage()
        if self._mutating and self.connection.monitor.stopped:
            raise LimitReached()
        result=method(*args)
        if self._mutating and not self.connection.in_transaction:
            self.connection.monitor.check(self.connection._connection)
        return result
    def fetchone(self): return self._finish(self._cursor.fetchone)
    def fetchmany(self, *args): return self._finish(self._cursor.fetchmany,*args)
    def fetchall(self): return self._finish(self._cursor.fetchall)
    def close(self):
        if not self._closed:
            self._closed=True
            self._finish(self._cursor.close)
    def __del__(self):
        # A discarded RETURNING cursor can finalize an autocommit write too.
        try: self.close()
        except BaseException:
            if self._mutating:
                self.connection.monitor.stopped=True
    def __getattr__(self, name):
        if name in ('rowcount','lastrowid','description','arraysize'):
            return getattr(self._cursor,name)
        raise AttributeError(name)


class ConnectionProxy:
    def __init__(self, connection, monitor, identity=None, *, read_only=False):
        self._connection, self.monitor = connection, monitor
        self.identity,self.read_only,self._closed=identity,read_only,False
        self._cursors=weakref.WeakSet()
        if read_only:
            return
        page_size = connection.execute('PRAGMA page_size').fetchone()[0]
        capped = connection.execute('PRAGMA max_page_count='+str(monitor.logical_limit//page_size)).fetchone()[0]
        if capped*page_size > monitor.logical_limit:
            connection.close()
            raise LimitReached()

    @property
    def row_factory(self): return self._connection.row_factory
    @row_factory.setter
    def row_factory(self, value): self._connection.row_factory=value
    @property
    def in_transaction(self): return self._connection.in_transaction
    @property
    def isolation_level(self): return self._connection.isolation_level
    @isolation_level.setter
    def isolation_level(self,value):
        if value is None and self.in_transaction:
            self.commit()
        self._connection.isolation_level=value

    @property
    def autocommit(self): return self._connection.autocommit
    @autocommit.setter
    def autocommit(self,value):
        # Available only on Python 3.12+; retain the native legacy mode contract.
        if not hasattr(self._connection,'autocommit'): raise AttributeError('autocommit')
        self.validate_storage()
        if self.monitor.stopped: raise LimitReached()
        if value is True and self.in_transaction:
            self.commit()
        self._connection.autocommit=value
        if not self.in_transaction: self.monitor.check(self._connection)

    def _execute(self, method, sql, parameters):
        read = _read_only(sql)
        self.validate_storage()
        if self.monitor.stopped and not read:
            raise LimitReached()
        try:
            result = method(sql,parameters)
        except sqlite3.DatabaseError as e:
            if getattr(e,'sqlite_errorcode',None) == sqlite3.SQLITE_FULL:
                self._connection.rollback()
                self.monitor.stopped=True
                raise LimitReached() from None
            raise
        if not self.in_transaction and not read:
            self.monitor.check(self._connection)
        return result

    def execute(self, sql, parameters=()):
        cursor=self._execute(self._connection.execute,sql,parameters)
        return CursorProxy(self,cursor,mutating=not _read_only(sql))
    def cursor(self):
        return CursorProxy(self,self._connection.cursor())
    def executemany(self, sql, parameters):
        return self.cursor().executemany(sql,parameters)
    def executescript(self, sql):
        if self.monitor.stopped:
            raise LimitReached()
        self.commit()
        prior=self.isolation_level
        self._connection.isolation_level=None
        current=''
        try:
            for char in sql:
                current+=char
                if char == ';' and sqlite3.complete_statement(current):
                    self.execute(current)
                    current=''
            if current.strip():
                self.execute(current)
        finally:
            self._connection.isolation_level=prior
        return self.cursor()
    def commit(self):
        self.validate_storage()
        if not self.in_transaction:
            return
        if self.monitor.stopped:
            raise LimitReached()
        self._connection.commit()
        self.monitor.check(self._connection)
    def rollback(self):
        self._connection.rollback()
    def __enter__(self): return self
    def __exit__(self, kind, value, traceback):
        if self.read_only:
            self.close()
            return False
        if kind:
            self.rollback()
        else:
            self.commit()
        return False
    def set_progress_handler(self, handler, steps):
        return self._connection.set_progress_handler(handler,steps)
    def backup(self, target, **kwargs):
        self.validate_storage()
        return self._connection.backup(target._connection if isinstance(target,ConnectionProxy) else target,**kwargs)
    def validate_storage(self):
        if self.monitor.invalid_storage:
            raise ContractError()
        if self.identity is not None:
            try:
                self.identity.validate(self._connection)
            except ContractError:
                self.monitor.stopped=True
                self.monitor.invalid_storage=True
                raise
    def close(self):
        if not self._closed:
            self._closed=True
            try:
                for cursor in list(self._cursors):
                    try: cursor.close()
                    except (LimitReached,ContractError): pass
                self._connection.close()
            finally:
                if self.identity is not None:
                    self.identity.close()


class OwnedSqlite:
    """Worker-local binding for Memory's connection factory only."""
    def __init__(self, capability, monitor):
        self.capability, self.monitor = capability, monitor
    def __getattr__(self, name):
        return getattr(sqlite3,name)
    def connect(self, path, *args, **kwargs):
        if self.monitor.invalid_storage:
            raise ContractError()
        if self.monitor.stopped:
            raise LimitReached()
        self.capability.validate()
        expected=self.capability.home/'memory.sqlite3'
        read_only=kwargs.get('uri') and str(path)==expected.as_uri()+'?mode=ro'
        if str(path) != str(expected) and not read_only:
            raise ContractError()
        identity=StorageIdentity(self.capability,writer=not read_only)
        connection=None
        try:
            # Every factory open is for an already-admitted existing DB.
            kwargs['uri']=True
            connection=CONNECT(expected.as_uri()+('?mode=ro' if read_only else '?mode=rw'),*args,**kwargs)
            identity.validate(connection)
            return ConnectionProxy(connection,self.monitor,identity,read_only=read_only)
        except BaseException:
            if connection is not None:
                connection.close()
            identity.close()
            self.monitor.stopped=True
            self.monitor.invalid_storage=True
            raise
