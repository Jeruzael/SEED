"""Complete disposable schema-v7 state through original Memory initialization."""
import json
import multiprocessing
import os
from pathlib import Path
import sqlite3
import threading
from .contracts import ContractError
from .paths import LearnerCapability
from .db_adapter import CONNECT, ConnectionProxy, GrowthMonitor, OwnedSqlite, LimitReached, StorageIdentity


def _worker_only():
    if multiprocessing.current_process().name != 'seed-evaluation-worker':
        raise ContractError()


class ReadFacade:
    def __init__(self, db, lock):
        self.db,self._lock=db,lock
    def get_q(self, key, action):
        with self._lock:
            r=self.db.execute('SELECT value,visits FROM q_values WHERE state_key=? AND action=?',(key,action)).fetchone()
            return (r[0],r[1]) if r else (0.0,0)
    def get_meta(self, key, default=None):
        with self._lock:
            r=self.db.execute('SELECT value FROM meta WHERE key=?',(key,)).fetchone()
            return json.loads(r[0]) if r else default


class OwnedState:
    def __init__(self, capability, memory, monitor):
        self.capability,self.memory,self.monitor=capability,memory,monitor
        self._closed=False

    @classmethod
    def fresh(cls, capability, public_settings):
        _worker_only()
        if type(capability) is not LearnerCapability:
            raise ContractError()
        capability.validate()
        if (capability.home/'memory.sqlite3').exists():
            raise ContractError()
        fd=capability.open('state','db','create')
        os.close(fd)
        from seed.config import validate_settings
        settings=validate_settings(public_settings)
        if settings.keys() - {'epsilon','alpha','observe_interval','reflect_interval','rest_interval','memory_budget','prediction_error_curiosity','advanced_concept_inference'}:
            raise ContractError()
        import seed.memory as module
        monitor=GrowthMonitor(capability.home)
        module.sqlite3=OwnedSqlite(capability,monitor)
        memory=module.Memory(capability.home/'memory.sqlite3')
        try:
            with memory.db:
                memory.db.execute('INSERT INTO settings(singleton,revision,data_json) VALUES(1,1,?) ON CONFLICT(singleton) DO UPDATE SET revision=1,data_json=excluded.data_json',
                                  (json.dumps(settings,sort_keys=True),))
            return cls(capability,memory,monitor)
        except BaseException:
            memory.close()
            raise

    def raw_tables(self):
        self.capability.validate()
        rows=self.memory.db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
        if len(rows)>64:
            raise LimitReached()
        result={}; count=0
        for row in rows:
            name=row[0]
            quoted='"'+name.replace('"','""')+'"'
            cols=self.memory.db.execute('PRAGMA table_info('+quoted+')').fetchall()
            order=','.join('"'+c[1].replace('"','""')+'"' for c in cols)
            cursor=self.memory.db.execute('SELECT * FROM '+quoted+' ORDER BY '+order)
            content=[]
            for item in cursor:
                count+=1
                if count>100000:
                    raise LimitReached()
                content.append([{'utf8_bytes':v.hex()} if isinstance(v,bytes) else v for v in item])
            result[name]=content
        return result

    def _backup(self, slot, kind, name):
        self.memory.db.validate_storage()
        self.memory.db.commit()
        slot.validate()
        logical=self.monitor.admit_backup(self.memory.db)
        fd=slot.open(kind,name,'create')
        os.close(fd)
        filename='checkpoint.sqlite3' if kind=='snapshot' else 'memory.sqlite3'
        path=slot.home/filename
        identity=None; target=None
        try:
            identity=StorageIdentity(slot,filename)
            target=CONNECT(path.as_uri()+'?mode=rw',uri=True)
            identity.validate(target)
            def progress(status, remaining, total):
                self.memory.db.validate_storage()
                identity.validate(target)
                self.monitor.check_backup(path,logical)
            self.memory.db.backup(target,pages=256,progress=progress)
            target.commit()
            identity.validate(target)
            self.memory.db.validate_storage()
            self.monitor.check_backup(path,logical)
            os.fsync(identity.fd)
            slot.sync()
        except BaseException:
            # Retain the owned incomplete prefix; never return it as trusted state.
            self.monitor.stopped=True
            raise
        finally:
            if target is not None: target.close()
            if identity is not None: identity.close()
        return path

    def checkpoint(self):
        return self._backup(self.capability,'snapshot','checkpoint')

    def clone(self, slot):
        _worker_only()
        self.capability.validate()
        if type(slot) is not LearnerCapability or slot.home.parent != self.capability.home.parent or slot.home==self.capability.home:
            raise ContractError()
        self._backup(slot,'state','db')
        import seed.memory as module
        monitor=GrowthMonitor(slot.home)
        module.sqlite3=OwnedSqlite(slot,monitor)
        memory=module.Memory(slot.home/'memory.sqlite3')
        return OwnedState(slot,memory,monitor)

    def close(self):
        if not self._closed:
            self._closed=True
            self.memory.close()
