"""Observe the unchanged cycle. This module has no parent scoring capability."""
import copy
import json
import threading
from .channel import wire_bytes
from .contracts import ContractError, PreUpdateEvidence, validate_event_key, validate_observation


def permitted(state):
    return validate_observation({k:v for k,v in state.items() if k in
        ('battery_pct','charging','load_ratio','disk_free_pct','network','local_hour')})


class SyntheticBody:
    def __init__(self, home, client, clock):
        self.home, self.client, self.clock = home, client, clock
        self.key = None
        self.action = None
        self.perceptions = 0
        self.capture = None

    def begin(self, key):
        self.key, self.action, self.perceptions = key, None, 0

    def perceive(self):
        if self.key is None or self.perceptions >= 2:
            raise ContractError()
        phase, subcase, ordinal, _ = self.key
        if self.perceptions == 0:
            state = self.client.observation(phase, ordinal, subcase)
            event = 'perception_before'
        else:
            if self.action is None:
                raise ContractError()
            state = self.client.apply(self.action, ordinal)
            event = 'perception_after'
        self.perceptions += 1
        if self.capture:
            self.capture.record['events'].append(event)
            self.capture.record['state_before' if self.perceptions == 1 else 'state_after'] = dict(state)
        # Ordinary producer metadata is controlled locally, absent on the wire.
        return {**state, 'wall_time':self.clock.wall()}


def construct_core(launch, streams, client):
    from seed import organism
    organism.Body = lambda home: SyntheticBody(home, client, streams.clock)
    if launch.launch_mode == 'FRESH':
        from .state import OwnedState
        state = OwnedState.fresh(launch.learner, json.loads(launch.settings))
        state.close()
        core = organism.SeedOrganism(launch.learner.home)
        core.decisions.rng = streams.learner_rng
        return core
    # Bind unchanged SeedOrganism methods to a completed owned clone without
    # reinitialization, migrations, recovery or changing its durable identity.
    from .state import CompletedLearner
    from seed.runtime import InstanceLock
    completed = CompletedLearner(launch.fixture, json.loads(launch.settings), streams)
    core = organism.SeedOrganism.__new__(organism.SeedOrganism)
    core.__dict__.update(completed.__dict__)
    core.home, core._closed = launch.learner.home, False
    try:
        core._instance = InstanceLock(core.home/'organism.lock').acquire()
        core.body = SyntheticBody(core.home, client, streams.clock)
        core.stop_event = threading.Event()
        core.last_tick_wall, core.sleep_threshold = streams.clock.wall(), 45.
        core.session_id = streams.uuids.next_hex('session')
        core._instance.identify(core.session_id)
        core.identity = core.memory.get_meta('identity')
        if not core.identity:
            raise ContractError()
        core._settings_revision = core.memory.db.execute('SELECT revision FROM settings WHERE singleton=1').fetchone()[0]
        return core
    except BaseException:
        completed.close()
        if hasattr(core,'_instance'):core._instance.close()
        raise


class CaptureSession:
    def __init__(self, client, clock):
        self.client, self.clock = client, clock
        self.core = None
        self.key = None
        self.record = {}
        self.acked = False
        self.failed = False
        self.b3_result = None

    def attach(self, core):
        if self.core is not None or type(core.body) is not SyntheticBody:
            raise ContractError()
        from seed import organism
        self.core = core
        self.original_b3 = organism.evaluate_prediction
        self._original_prepare = core.decisions.prepare
        self._original_select = core.decisions.select
        self._original_action = core.perform_action
        self._original_snapshot = core.decisions._snapshot
        self._original_beliefs = core.world_model.applicable_beliefs
        core.body.capture = self
        core.decisions._snapshot = self._snapshot
        core.decisions.prepare = self._prepare
        core.decisions.select = self._select
        core.perform_action = self._action
        core.world_model.applicable_beliefs = self._prior_beliefs
        organism.evaluate_prediction = self.evaluate_with_checkpoint
        core._evaluation_capture = self
        self._wrap_producer(core.learner,'update','q')
        self._wrap_producer(core.memory,'record_transition_experience','b1')
        self._wrap_producer(core.world_model,'recover','b4')
        self._wrap_producer(core.self_model,'update','b7',stage=4)

    def _wrap_producer(self, target, method, name, stage=3):
        original=getattr(target,method)
        def delegated(*args,**kwargs):
            if not self.acked:raise ContractError()
            self.clock.stage(self.key[0],self.key[2],stage)
            call=dict(status='started',result=None)
            self.record['producer_calls'][name]=call
            try:
                result=original(*args,**kwargs)
                call.update(status='returned',result=list(result) if type(result) is tuple else result)
                return result
            except BaseException:
                call['status']='raised'
                raise
        setattr(target,method,delegated)

    def begin(self, key):
        key = validate_event_key(list(key))
        if self.failed or self.core is None or key[3] != 'pre' or key[0] not in ('training','measured'):
            raise ContractError()
        self.key, self.acked, self.b3_result = key, False, None
        self.record = dict(events=[],driver='existing_cycle_adapter_v1',producer_calls={},prior_action_effects={})
        self.before_transition_id=self.core.memory.db.execute('SELECT COALESCE(MAX(id),0) FROM transitions').fetchone()[0]
        self.core.body.begin(key)

    def _snapshot(self, key):
        result = self._original_snapshot(key)
        self.record['q_snapshot'], self.record['history_rows'], _ = copy.deepcopy(result)
        return result

    def _prior_beliefs(self, action):
        # Observe the one original producer read at its original time. Do not
        # add a snapshot query or substitute the object passed to curiosity.
        result = self._original_beliefs(action)
        self.record['prior_b4'] = copy.deepcopy(result)
        self.record['prior_b4_action'] = action
        return result

    def _prepare(self, *args, **kwargs):
        if self.key is None or 'prepare' in self.record['events']:
            raise ContractError()
        result = self._original_prepare(*args, **kwargs)
        self.record['candidate_predictions'] = copy.deepcopy(result['batch'].predictions)
        self.record['candidate_contributors'] = copy.deepcopy(result['batch'].contributors)
        self.record['history'] = copy.deepcopy(result['history'])
        self.record['events'].append('prepare')
        return result

    def _select(self, prepared):
        if 'select' in self.record['events']:
            raise ContractError()
        result = self._original_select(prepared)
        self.record['selection'] = copy.deepcopy(result.record)
        self.record['selected_action'] = result.decision.action
        self.record['selected_prediction'] = copy.deepcopy(result.prediction)
        self.record['events'].append('select')
        self.core.body.action = result.decision.action
        self.clock.stage(self.key[0], self.key[2], 1)
        return result

    def _action(self, action, state=None):
        self.clock.stage(self.key[0], self.key[2], 1)
        self.record['events'].append('action')
        prior=self.core.memory.db.execute('SELECT COALESCE(MAX(id),0) FROM consolidation_runs').fetchone()[0]
        try:return self._original_action(action, state=state)
        finally:
            if action=='consolidate':
                self.record['prior_action_effects']['consolidation_runs']=[producer_payload(row) for row in
                    self.core.memory.db.execute('SELECT * FROM consolidation_runs WHERE id>? ORDER BY id',(prior,)).fetchall()]


    def evaluate_with_checkpoint(self, prediction, outcome):
        if 'b3' in self.record['events'] or prediction != self.record['selected_prediction']:
            self.failed = True
            raise ContractError()
        # The original pure result is the authority and retains object identity.
        result = self.original_b3(prediction, outcome)
        self.b3_result = result
        self.record['events'].append('b3')
        self.record['b3_result'] = result.to_dict()
        before = self.record['state_before']
        after = permitted(outcome)
        phase, subcase, ordinal, _ = self.key
        evidence = PreUpdateEvidence(wire_bytes(dict(phase=phase,subcase=subcase,transition_ordinal=ordinal,
            history_cutoff_id=self.record['history']['cutoff_transition_id'] or 0,
            state_before=before,selected_action=self.record['selected_action'],prediction=prediction,state_after=after)))
        self.record['events'].append('checkpoint')
        try:
            if self.client.send_checkpoint(evidence) != 'SCORE_ACK':
                raise ContractError()
            self.acked = True
            self.record['events'].append('ack')
            return result
        except BaseException:
            self.failed = True
            raise


def capture_updates(core, key):
    """Confirm real persisted producers even when a call raised after commit."""
    capture=core._evaluation_capture
    updates={name:dict(status='unconfirmed') for name in ('q','b1','b4','b5','b6','b7','b8')}
    capture.record['updates']=updates
    if not capture.acked:return updates
    db=core.memory.db
    selection=capture.record['selection']
    action=selection['selected_action']
    before=capture.record['q_snapshot'][action]
    after=core.memory.get_q(selection['state_key'],action)
    updates['q']=dict(status='confirmed' if after[1]==before['visits']+1 else 'unconfirmed',
                       before=before,after=dict(value=after[0],visits=after[1]))
    # B8 stores decision identity inside its unchanged JSON payload, not a
    # separate SQL column. Only the new single-writer row can confirm this event.
    row=db.execute('SELECT * FROM transitions WHERE id>? ORDER BY id DESC LIMIT 1',
                   (capture.before_transition_id,)).fetchone()
    if row is None:return updates
    tid=row['id']
    decision=db.execute('SELECT * FROM decision_records WHERE transition_id=?',(tid,)).fetchone()
    if decision is None or json.loads(decision['data_json'])['decision_id']!=selection['decision_id']:
        return updates
    episode=db.execute('SELECT * FROM episodes WHERE id=?',(row['episode_id'],)).fetchone()
    updates['b1']=dict(status='confirmed' if episode is not None else 'unconfirmed',transition_id=tid,
                       episode_id=row['episode_id'],transition=producer_payload(row),episode=producer_payload(episode))
    processed=db.execute('SELECT * FROM world_model_processed WHERE transition_id=?',(tid,)).fetchone()
    updates['b4']=dict(status='confirmed' if processed else 'unconfirmed',processed=dict(processed) if processed else None,
                       queued=db.execute('SELECT 1 FROM world_model_queue WHERE transition_id=?',(tid,)).fetchone() is not None)
    curiosity=db.execute('SELECT * FROM curiosity_assessments WHERE transition_id=?',(tid,)).fetchone()
    updates['b5']=dict(status='confirmed' if curiosity else 'unconfirmed',assessment=dict(curiosity) if curiosity else None)
    self_model=db.execute('SELECT * FROM self_model_current WHERE singleton=1').fetchone()
    updates['b7']=dict(status='confirmed' if self_model and self_model['source_transition_id']==tid else 'unconfirmed',
                       state=producer_payload(self_model),
                       producer_return=capture.record['producer_calls'].get('b7',{}).get('result'))
    updates['b8']=dict(status='confirmed' if decision else 'unconfirmed',record=producer_payload(decision))
    # B6 is not a current-transition implicit mutation. Selected consolidation
    # is prior-evidence work; declared maintenance is separately recorded.
    runs=capture.record['prior_action_effects'].get('consolidation_runs',[])
    updates['b6']=(dict(status='confirmed',scope='PRIOR_COMPLETED_EVIDENCE_ACTION',runs=runs) if runs else
                   dict(status='not_applicable',reason='NO_CURRENT_TRANSITION_CONSOLIDATION'))
    return updates


def producer_payload(row):
    if row is None:return None
    # Preserve original producer JSON bytes losslessly; individual wire strings
    # remain bounded, without changing source payloads or scientific projection.
    return {key:({'raw_json_chunks':[value[i:i+4096] for i in range(0,len(value),4096)]}
                 if key.endswith('_json') and type(value) is str else value) for key,value in dict(row).items()}
