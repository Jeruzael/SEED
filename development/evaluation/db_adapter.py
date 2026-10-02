"""External transaction guard; original producer SQL and schema are unchanged."""
import os
from pathlib import Path
import sqlite3
import stat
from .contracts import ContractError

CONNECT = sqlite3.connect


class LimitReached(RuntimeError):
    def __init__(self):
        super().__init__('LIMIT_REACHED')


class GrowthMonitor:
    def __init__(self, home, *, logical_limit=32*1024**2, physical_limit=64*1024**2, workspace_limit=128*1024**2):
        self.home = Path(home)
        self.logical_limit, self.physical_limit, self.workspace_limit = logical_limit, physical_limit, workspace_limit
        self.stopped, self.overshoot_exceeded = False, False
        self.commits = 0

    def check(self, connection):
        self.commits += 1
        logical = connection.execute('PRAGMA page_count').fetchone()[0] * connection.execute('PRAGMA page_size').fetchone()[0]
        physical = sum(p.stat().st_size for p in self.home.iterdir() if p.name in ('memory.sqlite3','memory.sqlite3-wal','memory.sqlite3-shm') and p.is_file())
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
        if logical > self.logical_limit or physical > self.physical_limit or workspace > self.workspace_limit:
            self.stopped = True
            self.overshoot_exceeded = physical > self.physical_limit+36*1024**2 or workspace > self.workspace_limit+36*1024**2
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
    def __init__(self, connection, cursor):
        self.connection, self._cursor = connection, cursor
    def execute(self, sql, parameters=()):
        self.connection._execute(self._cursor.execute,sql,parameters)
        return self
    def executemany(self, sql, parameters):
        # Individual executions also cover autocommit producers.
        for row in parameters:
            self.execute(sql,row)
        return self
    def __iter__(self):
        return iter(self._cursor)
    def __getattr__(self, name):
        if name in ('fetchone','fetchmany','fetchall','close','rowcount','lastrowid','description','arraysize'):
            return getattr(self._cursor,name)
        raise AttributeError(name)


class ConnectionProxy:
    def __init__(self, connection, monitor):
        self._connection, self.monitor = connection, monitor
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

    def _execute(self, method, sql, parameters):
        read = _read_only(sql)
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
        return CursorProxy(self,cursor)
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
        if kind:
            self.rollback()
        else:
            self.commit()
        return False
    def set_progress_handler(self, handler, steps):
        return self._connection.set_progress_handler(handler,steps)
    def backup(self, target, **kwargs):
        return self._connection.backup(target._connection if isinstance(target,ConnectionProxy) else target,**kwargs)
    def close(self):
        self._connection.close()


class OwnedSqlite:
    """Worker-local binding for Memory's connection factory only."""
    def __init__(self, capability, monitor):
        self.capability, self.monitor = capability, monitor
    def __getattr__(self, name):
        return getattr(sqlite3,name)
    def connect(self, path, *args, **kwargs):
        self.capability.validate()
        expected=self.capability.home/'memory.sqlite3'
        read_only=kwargs.get('uri') and str(path)==expected.as_uri()+'?mode=ro'
        if str(path) != str(expected) and not read_only:
            raise ContractError()
        for suffix in ('','-wal','-shm','-journal'):
            file=Path(str(expected)+suffix)
            if file.exists() or file.is_symlink():
                st=file.lstat()
                if not stat.S_ISREG(st.st_mode) or st.st_uid != os.geteuid() or st.st_nlink != 1:
                    raise ContractError()
        connection=CONNECT(path,*args,**kwargs)
        if read_only:
            return connection
        return ConnectionProxy(connection,self.monitor)
