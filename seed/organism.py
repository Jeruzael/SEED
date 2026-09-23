from __future__ import annotations
import json
import logging
import os
import statistics
import threading
import time
import uuid
from dataclasses import asdict
from pathlib import Path

from .body import Body
from .learner import Learner
from .predictor import Predictor
from .prediction_error import evaluate_prediction
from .world_model import WorldModel
from .curiosity import assess_curiosity
from .curiosity_attention import CuriosityAttention, summary as curiosity_summary
from .memory import Memory
from .runtime import InstanceLock
from .telemetry import Telemetry
from .commands import CommandQueue
from .config import DEFAULTS, validate_settings
from .transitions import validated_state, describe_outcome

log = logging.getLogger('seed')


class SeedOrganism:
    def __init__(self, home: Path):
        self.home = Path(home)
        self._closed = False
        self._instance = InstanceLock(self.home / 'organism.lock').acquire()
        try:
            self.memory = Memory(self.home / 'memory.sqlite3')
            self.body = Body(self.home)
            self.learner = Learner(self.memory)
            self.predictor = Predictor(self.memory)
            self.world_model = WorldModel(self.memory)
            self.world_model.recover()
            self.curiosity_attention = CuriosityAttention(self.memory)
            self.telemetry = Telemetry(self.memory)
            self.stop_event = threading.Event()
            self.last_tick_wall = time.time()
            self.sleep_threshold = 45.0
            self.session_id = uuid.uuid4().hex
            self._instance.identify(self.session_id)
            self.commands = CommandQueue(self.memory)
            self.commands.recover(self.session_id)
            self.identity = self.memory.get_meta('identity')
            if not self.identity:
                self.identity = {
                    'name': 'SEED', 'born_at': time.time(), 'generation': 0,
                    'principles': ['operate only while authorized', 'never prevent sleep or shutdown',
                                   'never replicate or persist outside the configured home',
                                   'learn by observation before action', 'preserve memory integrity'],
                }
                self.memory.set_meta('identity', self.identity)
            self._settings_revision = -1
            self.apply_settings()
            self.telemetry.runtime(session_id=self.session_id, pid=os.getpid(), started_at=time.time(),
                                   heartbeat=time.time(), lifecycle='STARTING', activity='starting',
                                   action_started_at=time.time(), last_error=None, version='0.1')
        except BaseException:
            if hasattr(self, 'memory'):
                self.memory.close()
            self._instance.close()
            raise

    def apply_settings(self):
        row = self.memory.db.execute('SELECT revision,data_json FROM settings WHERE singleton=1').fetchone()
        revision = row[0] if row else 0
        if revision == self._settings_revision:
            return
        config = {**DEFAULTS, **validate_settings(json.loads(row[1]) if row else {})}
        self.config = config
        self.learner.epsilon, self.learner.alpha = config['epsilon'], config['alpha']
        if self.identity['name'] != config['name'] and row:
            self.identity['name'] = config['name']
            self.memory.set_meta('identity', self.identity)
        self._settings_revision = revision
        self.telemetry.runtime(settings_revision=revision, effective_settings=config)
        for handler in log.handlers:
            if hasattr(handler, 'maxBytes'):
                handler.maxBytes, handler.backupCount = config['log_bytes'], config['log_count']

    def awaken(self, reason='process_start'):
        state = self.body.perceive()
        self.memory.episode('wake', state, note=reason)
        self.memory.set_meta('last_wake', time.time())
        self.telemetry.emit('LIFECYCLE', 'organism', 'Wake recorded',
                            {'reason': reason, 'inferred': reason.startswith('resume_after_')})
        self.telemetry.runtime(lifecycle='AWAKE', heartbeat=time.time())
        log.info('awake: %s', reason)

    def sleep(self, reason='system_sleep'):
        # Shutdown must not block on fresh network or battery sensing.
        state = self.memory.get_meta('last_state', {})
        self.memory.episode('sleep', state, note=reason)
        self.memory.set_meta('last_sleep', time.time())
        self.telemetry.emit('LIFECYCLE', 'organism', 'Stopped' if reason == 'process_stop' else 'Sleep recorded', {'reason': reason})
        self.telemetry.runtime(lifecycle='STOPPED' if reason == 'process_stop' else 'SLEEPING',
                               activity='stopped', heartbeat=time.time(), next_observation_at=None)
        log.info('sleep: %s', reason)

    def infer_wake_if_needed(self):
        now = time.time()
        gap = now - self.last_tick_wall
        if gap > self.sleep_threshold:
            self.awaken(reason=f'resume_after_{round(gap, 1)}s_gap')
        self.last_tick_wall = now

    def reflect(self, provenance='policy_selected', transition_id=None):
        self.telemetry.emit('REFLECTION', 'reflection', 'Internal reflection started',
                            {'provenance': provenance, 'transition_id': transition_id})
        states = []
        for row in self.memory.recent_episodes(80):
            try:
                state = json.loads(row['state_json'])
                if isinstance(state, dict) and state.get('source') != 'owner':
                    states.append((row['id'], state))
            except (ValueError, TypeError):
                continue
        for name, key, field, digits, types in [
            ('typical_compute_pressure', 'load_ratio', 'mean_load_ratio', 3, (int, float)),
            ('typical_observed_battery', 'battery_pct', 'mean_battery_pct', 1, (int,)),
        ]:
            samples = [(eid, state[key]) for eid, state in states if isinstance(state.get(key), types)]
            if len(samples) < 8:
                continue
            payload = {field: round(statistics.fmean(value for _, value in samples), digits)}
            confidence = min(.95, .4 + len(samples) / 200)
            old = self.memory.db.execute('SELECT confidence FROM concepts WHERE name=?', (name,)).fetchone()
            self.memory.upsert_concept(name, confidence, len(samples), payload)
            with self.memory._lock, self.memory.db:
                self.memory.db.execute('''INSERT INTO concept_evidence VALUES(?,?,?,?)
                ON CONFLICT(name) DO UPDATE SET updated_at=excluded.updated_at,episode_ids_json=excluded.episode_ids_json''',
                                       (name, None if old else time.time(), time.time(), json.dumps([i for i, _ in samples])))
            self.telemetry.emit('CONCEPT', 'reflection', f'Updated {name}',
                                {'name': name, 'confidence': confidence, 'previous_confidence': old[0] if old else None,
                                 'evidence': len(samples), 'payload': payload,
                                 'provenance': provenance, 'transition_id': transition_id})

    def consolidate(self):
        self.memory.set_meta('last_consolidation', {'at': time.time(), **self.memory.stats()})
        self.telemetry.emit('MEMORY', 'organism', 'Consolidation checkpoint recorded; memories preserved', {})

    def perform_action(self, action):
        # Observe/rest have no additional internal processing. Rest's wait is later.
        if action == 'reflect':
            self.reflect()
        elif action == 'consolidate':
            self.consolidate()

    def cycle(self):
        self.apply_settings()
        self.infer_wake_if_needed()
        self.telemetry.runtime(activity='observing', current_action=None,
                               action_started_at=time.time(), heartbeat=time.time())
        state_before = validated_state(self.body.perceive())
        self.telemetry.emit('PERCEPTION', 'body', 'Environment observed before action',
                            {**state_before, 'phase': 'before_action'})
        decision = self.learner.choose(state_before)
        self.telemetry.emit('DECISION', 'learner', f'Selected {decision.action.upper()}', asdict(decision))
        prediction = self.predictor.predict(state_before, decision.action).to_dict()
        self.telemetry.emit('PREDICTION', 'predictor', 'Prediction generated for immediate post-action observation',
                            prediction)
        started_at = time.time()
        self.telemetry.runtime(activity=decision.action, current_action=decision.action,
                               action_started_at=started_at, context=decision.state_key,
                               last_decision=asdict(decision))
        self.telemetry.emit('ACTION', 'organism', f'Started {decision.action}',
                            {'action': decision.action, 'phase': 'start'})
        self.perform_action(decision.action)
        self.telemetry.emit('ACTION', 'organism', f'Completed {decision.action}',
                            {'action': decision.action, 'phase': 'complete'})
        self.telemetry.runtime(activity='observing', current_action=None,
                               last_completed_action=decision.action, last_action_completed_at=time.time())
        state_after = validated_state(self.body.perceive())
        completed_at = time.time()
        self.telemetry.emit('PERCEPTION', 'body', 'Environment observed after action',
                            {**state_after, 'phase': 'after_action'})
        outcome = describe_outcome(state_before, state_after)
        prediction_error = evaluate_prediction(prediction, state_after).to_dict()
        self.telemetry.emit('PREDICTION_ERROR', 'prediction_error', 'Prospective prediction evaluated',
                            prediction_error)
        curiosity = assess_curiosity(prediction_error, state_before, decision.action, state_after,
                                     self.world_model.applicable_beliefs(decision.action))
        # B1 intentionally preserves B0 reward inputs; only evaluation timing changes.
        reward = self.learner.reward(state_before, decision.action)
        self.learner.update(decision, reward)
        new, visits = self.memory.get_q(decision.state_key, decision.action)
        episode_id, transition_id = self.memory.record_transition_experience(
            state_before=state_before, action=decision.action, state_after=state_after,
            outcome=outcome, legacy_reward=reward, started_at=started_at,
            completed_at=completed_at, note=f'context={decision.state_key}', prediction=prediction,
            prediction_error=prediction_error, world_model_eligible=True, curiosity=curiosity)
        self.telemetry.emit('CURIOSITY', 'curiosity', 'Curiosity assessment recorded',
                            {**curiosity_summary({**curiosity, 'transition_id': transition_id}, 'assessed'),
                             'suppression_reason': curiosity['suppression_reason']})
        self.world_model.recover()
        self.telemetry.emit('LEARNING', 'learner', 'Updated action value using legacy reward',
                            {'state_key': decision.state_key, 'action': decision.action, 'old_value': decision.score,
                             'new_value': new, 'visits': visits, 'reward': reward, 'alpha': self.learner.alpha,
                             'transition_id': transition_id, 'episode_id': episode_id})
        self.telemetry.emit('MEMORY', 'memory', f'Stored transition #{transition_id} and episode #{episode_id}',
                            {'episode_id': episode_id, 'transition_id': transition_id})
        self.memory.set_meta('last_state', state_after)
        self.memory.set_meta('last_action', decision.action)
        self.curiosity_attention.execute(transition_id,
            lambda: self.reflect(provenance='curiosity_triggered', transition_id=transition_id),
            self.stop_event, enabled=self.config['prediction_error_curiosity'])
        delay = {'observe': self.config['observe_interval'], 'reflect': self.config['reflect_interval'],
                 'consolidate': 20, 'rest': self.config['rest_interval']}[decision.action]
        self.telemetry.runtime(lifecycle='AWAKE', activity='resting' if decision.action == 'rest' else 'idle',
                               action_started_at=time.time(), last_action=decision.action, last_reward=reward,
                               heartbeat=time.time(), last_successful_cycle=time.time(), next_observation_at=time.time() + delay,
                               epsilon=self.learner.epsilon, alpha=self.learner.alpha)
        return delay

    def process_commands(self):
        if self.stop_event.is_set():
            return
        request = self.commands.claim(self.session_id)
        if not request:
            return
        name = request['name']
        try:
            self.telemetry.runtime(activity=name, action_started_at=time.time())
            if name == 'observe':
                state = self.body.perceive()
                episode_id = self.memory.episode('experience', state, action='observe', note='source=owner_command')
                self.memory.set_meta('last_state', state)
                result = {'episode_id':episode_id}
                self.telemetry.emit('PERCEPTION', 'owner_command', 'Owner-requested observation', state)
            elif name == 'reflect':
                self.reflect(provenance='owner_requested')
                result = {'message':'Reflection completed'}
            elif name == 'consolidate':
                self.consolidate()
                result = {'message':'Checkpoint recorded; all memories preserved'}
            elif name == 'rotate_logs':
                handlers = [h for h in log.handlers if hasattr(h, 'doRollover')]
                if not handlers:
                    raise ValueError('Managed logging is unavailable; deploy the logging upgrade first')
                for handler in handlers:
                    handler.doRollover()
                result = {'message':'Managed core logs rotated'}
            else:
                raise ValueError('Unsupported core command')
            self.commands.complete(request['id'], result)
        except Exception as error:
            self.commands.fail(request['id'], str(error)[:300])
        finally:
            self.telemetry.runtime(activity='idle', action_started_at=time.time(), heartbeat=time.time())

    def run(self):
        failed = False
        try:
            self.awaken()
            while not self.stop_event.is_set():
                delay = self.cycle()
                deadline = time.monotonic() + delay
                while not self.stop_event.is_set() and time.monotonic() < deadline:
                    self.stop_event.wait(min(2, max(0, deadline - time.monotonic())))
                    self.telemetry.runtime(heartbeat=time.time())
                    self.process_commands()
        except Exception as error:
            failed = True
            self.telemetry.emit('ERROR', 'organism', 'SEED requires attention', {'error': str(error)[:500]})
            self.telemetry.runtime(lifecycle='ERROR', activity='error', last_error=str(error)[:500], heartbeat=time.time())
            log.exception('SEED requires attention')
            raise
        finally:
            try:
                if not failed:
                    self.sleep(reason='process_stop')
            finally:
                self.close()

    def stop(self):
        self.stop_event.set()

    def close(self):
        if not self._closed:
            try:
                self.memory.close()
            finally:
                self._instance.close()
                self._closed = True
