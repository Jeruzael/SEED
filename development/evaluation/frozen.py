"""Read-only selection assays over an exact completed owned checkpoint."""
import copy
import math
import os
import sqlite3
import threading
from .contracts import ContractError, CompletedEvidence, validate_event_key, validate_observation
from .channel import wire_bytes
from .db_adapter import CONNECT, StorageIdentity, LimitReached
from .state import CompletedFixture, ReadFacade, OwnedState, _worker_only


def freeze_state(owned, *, close_owner=None):
    _worker_only()
    if type(owned) is not OwnedState or owned._closed or owned.monitor.stopped:
        raise ContractError()
    db=owned.memory.db
    if db.in_transaction or db.execute("SELECT 1 FROM commands WHERE status IN ('pending','running') LIMIT 1").fetchone():
        raise ContractError()
    # Bound draining by the declared maximum completed training prefix. Lack
    # of progress is incomplete work, never a repaired frozen probe.
    from seed.world_model import WorldModel
    model=WorldModel(owned.memory)
    for _ in range(513):
        count=db.execute('SELECT COUNT(*) FROM world_model_queue').fetchone()[0]
        if not count:break
        if count>512 or model.recover()<=0:
            raise ContractError()
    else:raise ContractError()
    owned.checkpoint()
    return owned.complete_fixture(close_owner=close_owner)


class _ReadConnection:
    def __init__(self, owner, db):self.owner,self.db=owner,db
    def execute(self, sql, parameters=()):
        if sql.strip().upper().startswith(('BEGIN IMMEDIATE','BEGIN EXCLUSIVE')):
            self.owner.failed=True
            raise sqlite3.DatabaseError('FROZEN_WRITE_FORBIDDEN')
        return self.db.execute(sql,parameters)
    def __getattr__(self,name):return getattr(self.db,name)


class FrozenWorker:
    def __init__(self, fixture, streams):
        _worker_only()
        if type(fixture) is not CompletedFixture:raise ContractError()
        fixture.validate()
        self.capability=fixture.learner
        self.streams=streams
        self.failed=False
        self.identity=StorageIdentity(self.capability,writer=False)
        self._connection=None
        try:
            path=self.capability.home/'memory.sqlite3'
            self._connection=CONNECT(path.as_uri()+'?mode=ro&immutable=1',uri=True,check_same_thread=False)
            self.identity.validate(self._connection)
            self._connection.row_factory=sqlite3.Row
            self._connection.execute('PRAGMA query_only=ON')
            self._connection.set_authorizer(self._authorize)
            self.memory=ReadFacade(_ReadConnection(self,self._connection),threading.RLock())
            from seed.learner import Learner
            from seed.predictor import Predictor
            from seed.decision import DecisionSystem
            from seed.config import DEFAULTS,validate_settings
            self.learner=Learner(self.memory)
            settings=self._connection.execute('SELECT data_json FROM settings WHERE singleton=1').fetchone()
            import json
            config={**DEFAULTS,**validate_settings(json.loads(settings[0]))}
            self.learner.epsilon,self.learner.alpha=config['epsilon'],config['alpha']
            self.decisions=DecisionSystem(self.memory,Predictor(self.memory),self.learner,rng=streams.learner_rng)
            self._before=self.raw_state()
            self._last={}
        except BaseException:
            self.close()
            raise

    def _authorize(self, operation, one, two, database, trigger):
        if operation in (sqlite3.SQLITE_READ,sqlite3.SQLITE_SELECT,sqlite3.SQLITE_TRANSACTION):
            return sqlite3.SQLITE_OK
        if operation==sqlite3.SQLITE_FUNCTION and two!='load_extension':
            return sqlite3.SQLITE_OK
        if operation==sqlite3.SQLITE_PRAGMA:
            read=('table_info','database_list','schema_version','user_version','page_size','page_count',
                  'integrity_check','foreign_key_check','query_only','busy_timeout')
            if one.lower() in read and two is None:return sqlite3.SQLITE_OK
            # SQLite reports the table argument as arg2 even though these
            # introspection PRAGMAs do not assign or mutate persistent state.
            if one.lower() in ('table_info','foreign_key_check','integrity_check'):
                return sqlite3.SQLITE_OK
            if one.lower()=='busy_timeout' and two is not None and two.isdigit() and 0<=int(two)<=5000:
                return sqlite3.SQLITE_OK
        self.failed=True
        return sqlite3.SQLITE_DENY

    def raw_state(self):
        self.identity.validate(self._connection)
        tables=OwnedState.raw_tables(self)
        schema=[list(row) for row in self._connection.execute(
            'SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name')]
        fd=self.capability.open('state','db','read')
        with os.fdopen(fd,'rb') as file:raw=file.read(32*1024**2+1)
        if len(raw)>32*1024**2:raise LimitReached()
        return dict(tables=tables,schema=schema,db_bytes=raw)

    def assert_unchanged(self):
        if self.raw_state()!=self._before:self.failed=True
        if self.failed:raise ContractError()

    def probe(self, observation, key, client, *, read_time=None):
        if self.failed:raise ContractError()
        key=validate_event_key(list(key))
        if key[0]!='probe' or key[3]!='pre' or key[2]!=self._last.get(key[:2],0)+1:
            self.failed=True
            raise ContractError()
        before=validate_observation(observation)
        self.streams.clock.stage(key[0],key[2],0)
        if read_time is not None and (type(read_time) not in (int,float) or not math.isfinite(read_time) or read_time<0):
            self.failed=True
            raise ContractError()
        prepared=self.decisions.prepare(before,selected_at=self.streams.clock.wall() if read_time is None else read_time)
        # The reader may not disguise an authorizer rejection as a producer fallback.
        self.assert_unchanged()
        selection=self.decisions.select(prepared)
        self.streams.clock.stage(key[0],key[2],1)
        after=client.apply(selection.decision.action,key[2])
        self.streams.clock.stage(key[0],key[2],2)
        from seed.prediction_error import evaluate_prediction
        result=dict(driver='frozen_projection_v1',assay_kind='FROZEN_SELECTION_ASSAY',
            read_time=prepared['selected_at'],
            internal_action_effects='suppressed_by_protocol',state_before=before,state_after=after,
            candidate_predictions=copy.deepcopy(prepared['batch'].predictions),selection=copy.deepcopy(selection.record),
            prediction=copy.deepcopy(selection.prediction),b3_projection=evaluate_prediction(selection.prediction,after).to_dict())
        self.assert_unchanged()
        self._last[key[:2]]=key[2]
        return CompletedEvidence(key,wire_bytes(result))

    def close(self):
        try:
            if self._connection is not None:self._connection.close()
        finally:self.identity.close()
