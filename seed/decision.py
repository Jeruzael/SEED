"""Bounded selection-time evidence and fixed B8 utility policy."""
from dataclasses import dataclass
import copy
import math
import random
import sqlite3
import uuid
from .learner import ACTIONS, Decision, state_key
from .predictor import NUMERIC_TARGETS, empty_history_batch
from .semantic_memory import resource_suppression
from .decision_record import (CONTRACT, MAX_ID, compact, number, integer, validate_state,
                              projection, validate_prediction, prediction_digest, validate_record)

READ_BUDGET = 100000


@dataclass(frozen=True)
class Selection:
    decision: Decision
    prediction: dict
    record: dict
    state_before: dict

    def validate(self):
        certify_record(self.record, prediction=self.prediction, state_before=self.state_before, draft=True)


def constraints(state, action):
    if action in ('observe', 'rest'):
        return []
    reasons = []
    if state.get('load_ratio',0) > .8:
        reasons.append('high_load')
    if state.get('battery_pct') is not None and state['battery_pct'] < 20 and state.get('charging') is False:
        reasons.append('low_battery')
    if state.get('disk_free_pct',100) < 10:
        reasons.append('low_disk')
    known = resource_suppression(state)
    if known is not None and (not reasons or reasons[0] != known):
        raise ValueError('invalid_resource_contract')
    if any(state.get(key) is None for key in ('battery_pct','charging','load_ratio','disk_free_pct')):
        reasons.append('unknown_resources')
    return reasons


def components(q, forecasts, state):
    risks, uncertainty = [], []
    for target in NUMERIC_TARGETS:
        signal = forecasts[target]
        risk, unknown = 1., 1.
        if signal['status']=='usable':
            value = signal['value']
            if target=='battery_pct':
                risk = 0 if state.get('charging') is True else (40-value)/40
            elif target=='load_ratio':
                risk = (value-.5)/.5
            else:
                risk = (20-value)/20
            risk = min(1.,max(0.,risk))
            unknown = 1-signal['confidence']
        risks.append(risk)
        uncertainty.append(unknown)
    qpart = min(1.,max(0.,.5+.5*(q/(1+abs(q)))))
    result = dict(q_component=qpart,forecast_resource_risk=sum(risks)/3,model_uncertainty=sum(uncertainty)/3)
    utility = .50*qpart + .35*(1-result['forecast_resource_risk']) + .15*(1-result['model_uncertainty'])
    return result,min(1.,max(0.,utility))


def certify_record(record, *, prediction, state_before, draft=False):
    """Writer-only formula/guard/pool certification; never used by observer reads."""
    validate_record(record, prediction=prediction, state_before=state_before, draft=draft)
    candidates = record['candidates']
    for action in ACTIONS:
        c = candidates[action]
        parts, utility = components(c['q_value'],c['resource_forecasts'],state_before)
        if (c['constraint_reasons'] != constraints(state_before,action) or
                c['components'] != parts or c['decision_utility'] != utility):
            raise ValueError('invalid_decision_certification')
    eligible = record['eligible_actions']
    supported = any(s['status']=='usable' for a in eligible for s in candidates[a]['resource_forecasts'].values())
    basis = 'composite' if supported else 'legacy_q'
    reason = None if supported else record['history']['reason'] or 'no_supported_resource_forecast'
    if record['policy_basis'] != basis or record['fallback_reason'] != reason:
        raise ValueError('invalid_decision_certification')
    if record['random_draw'] < record['epsilon']:
        pool = eligible
    else:
        field = 'decision_utility' if supported else 'q_value'
        maximum = max(candidates[a][field] for a in eligible)
        pool = [a for a in eligible if (abs(candidates[a][field]-maximum)<=1e-12 if supported else candidates[a][field]==maximum)]
    if record['selection_candidates'] != pool:
        raise ValueError('invalid_decision_certification')
    return record


class DecisionSystem:
    def __init__(self, memory, predictor, learner, *, rng=None):
        self.memory,self.predictor,self.learner = memory,predictor,learner
        self.rng = random if rng is None else rng

    def _snapshot(self,key):
        db = self.memory.db
        qrows, rows, reason = [], [], None
        with self.memory._lock:
            if db.in_transaction:
                raise ValueError('decision_existing_transaction')
            timeout = db.execute('PRAGMA busy_timeout').fetchone()[0]
            owned, used, primary, cleanup = False, 0, None, None
            def progress():
                nonlocal used
                used += 1000
                return used >= READ_BUDGET
            try:
                db.execute('PRAGMA busy_timeout=0')
                db.set_progress_handler(progress,1000)
                db.execute('BEGIN')
                owned = True
                qrows = db.execute('''SELECT action,
                    CASE WHEN typeof(value) IN ('integer','real') THEN value ELSE 'invalid' END AS value,
                    CASE WHEN typeof(visits)='integer' THEN visits ELSE 'invalid' END AS visits
                    FROM q_values WHERE state_key=? AND action IN ('observe','reflect','consolidate','rest')''',(key,)).fetchall()
                for row in qrows:
                    if not number(row['value']) or not integer(row['visits'],0,MAX_ID-1):
                        raise ValueError('invalid_q')
                try:
                    rows = [dict(row) for row in db.execute('''SELECT id,
                        CASE WHEN typeof(completed_at) IN ('integer','real') THEN completed_at ELSE NULL END AS completed_at,
                        CASE WHEN action IN ('observe','reflect','consolidate','rest') THEN action ELSE 'unknown' END AS action,
                        CASE WHEN length(CAST(state_before_json AS BLOB))<=16384 THEN state_before_json ELSE NULL END AS state_before_json,
                        CASE WHEN length(CAST(state_after_json AS BLOB))<=16384 THEN state_after_json ELSE NULL END AS state_after_json
                        FROM transitions ORDER BY id DESC LIMIT 200''').fetchall()]
                except sqlite3.Error:
                    reason = 'history_budget_exceeded' if used >= READ_BUDGET else 'history_read_error'
            except BaseException as error:
                primary = error
            finally:
                # Independent cleanup attempts: never disguise an unsafe connection as fallback.
                for operation in (lambda: db.rollback() if owned and db.in_transaction else None,
                                  lambda: db.set_progress_handler(None,0),
                                  lambda: db.execute(f'PRAGMA busy_timeout={int(timeout)}')):
                    try:
                        operation()
                    except BaseException as error:
                        if cleanup is None:
                            cleanup = error
                if primary is not None and isinstance(primary,(KeyboardInterrupt,SystemExit)):
                    raise primary
                if cleanup is not None:
                    raise RuntimeError('decision_read_cleanup_failed') from cleanup
                if primary is not None:
                    raise primary
        history = dict(status='ok' if rows else 'empty',reason=None,
                       cutoff_transition_id=max((r['id'] for r in rows),default=None),raw_rows_examined=len(rows))
        if any(r['state_before_json'] is None or r['state_after_json'] is None for r in rows):
            reason = 'oversized_history'
        if reason:
            history.update(status='unavailable',reason=reason)
            rows=[]
        q = {a:dict(q_value=0.,visits=0,q_missing=True) for a in ACTIONS}
        for row in qrows:
            q[row['action']] = dict(q_value=row['value'],visits=row['visits'],q_missing=False)
        return q,rows,history

    def prepare(self,state,*,selected_at,decision_id=None):
        state = validate_state(state)
        if not number(selected_at,0):
            raise ValueError('invalid_decision_clock')
        epsilon,alpha=self.learner.epsilon,self.learner.alpha
        if not number(epsilon,0,1) or not number(alpha,0,1) or alpha==0:
            raise ValueError('invalid_decision_settings')
        attempt_id = uuid.uuid4().hex if decision_id is None else decision_id
        key=state_key(state)
        q,rows,history = self._snapshot(key)
        try:
            batch = self.predictor.predict_candidates(state,ACTIONS,snapshot=rows)
            if set(batch.predictions)!=set(ACTIONS) or set(batch.contributors)!=set(ACTIONS):
                raise ValueError('invalid_prediction')
            for action in ACTIONS:
                validate_prediction(batch.predictions[action],action)
                if set(batch.contributors[action])!=set(NUMERIC_TARGETS):
                    raise ValueError('invalid_prediction')
            candidates=self._candidates(q,batch,state,selected_at)
            # Validate transient contributor projections as well as the full payload.
            self._draft(state,key,selected_at,attempt_id,epsilon,alpha,history,batch,candidates,.5,validate_only=True)
        except (ValueError,TypeError,KeyError,OverflowError,AttributeError,RecursionError):
            history.update(status='unavailable',reason='invalid_prediction')
            batch=empty_history_batch(state,ACTIONS)
            candidates=self._candidates(q,batch,state,selected_at)
        return dict(state=state,key=key,selected_at=selected_at,decision_id=attempt_id,
                    epsilon=epsilon,alpha=alpha,history=history,batch=batch,candidates=candidates)

    @staticmethod
    def _candidates(q,batch,state,selected_at):
        candidates={}
        for action in ACTIONS:
            forecasts={}
            for target in NUMERIC_TARGETS:
                signal=batch.predictions[action]['signals'][target]
                source=batch.contributors[action][target]
                status='unavailable' if signal['status']=='unavailable' else 'persistence'
                if signal['evidence_count']:
                    clock=source['newest_source_completed_at']
                    status=('invalid' if source['invalid_source_count'] or clock>selected_at else
                            'stale' if selected_at-clock>300 else 'usable')
                forecasts[target]=dict(status=status,value=signal.get('value'),method=signal.get('method'),
                                       evidence_count=signal['evidence_count'],confidence=signal['confidence'],**source)
            reasons=constraints(state,action)
            parts,utility=components(q[action]['q_value'],forecasts,state)
            candidates[action]=dict(**q[action],eligible=not reasons,constraint_reasons=reasons,
                                    components=parts,decision_utility=utility,resource_forecasts=forecasts)
        return candidates

    def _draft(self,state,key,selected_at,decision_id,epsilon,alpha,history,batch,candidates,draw,validate_only=False):
        eligible=[a for a in ACTIONS if candidates[a]['eligible']]
        supported=any(s['status']=='usable' for a in eligible for s in candidates[a]['resource_forecasts'].values())
        basis='composite' if supported else 'legacy_q'
        reason=None if supported else history['reason'] or 'no_supported_resource_forecast'
        if not eligible:
            raise ValueError('invalid_eligibility_contract')
        exploration=draw<epsilon
        if exploration:
            pool=eligible[:]
        elif supported:
            maximum=max(candidates[a]['decision_utility'] for a in eligible)
            pool=[a for a in eligible if abs(candidates[a]['decision_utility']-maximum)<=1e-12]
        else:
            maximum=max(candidates[a]['q_value'] for a in eligible)
            pool=[a for a in eligible if candidates[a]['q_value']==maximum]
        action=pool[0] if len(pool)==1 or validate_only else self.rng.choice(pool)
        if action not in pool:
            raise ValueError('invalid_rng_choice')
        record=dict(model='decision_v1',model_version=1,weights_version=1,decision_id=decision_id,
                    transition_id=None,created_at=None,selected_at=selected_at,state_key=key,current=projection(state),
                    history=history,prediction_contract=CONTRACT.copy(),selected_prediction_sha256=prediction_digest(batch.predictions[action]),
                    epsilon=epsilon,alpha=alpha,random_draw=draw,choice_index=None if len(pool)==1 else pool.index(action),
                    policy_basis=basis,selection_mode='explore' if exploration else 'exploit' if supported else 'fallback',
                    eligible_actions=eligible,selection_candidates=pool,selected_action=action,fallback_reason=reason,candidates=candidates)
        prediction=copy.deepcopy(batch.predictions[action])
        certify_record(record,prediction=prediction,state_before=state,draft=True)
        decision=Decision(key,action,candidates[action]['q_value'],{a:candidates[a]['q_value'] for a in ACTIONS},
                          {a:candidates[a]['visits'] for a in ACTIONS},exploration,epsilon,pool[:])
        return Selection(decision,prediction,copy.deepcopy(record),copy.deepcopy(state))

    def select(self,prepared):
        draw=self.rng.random()
        if not number(draw,0,1) or draw>=1:
            raise ValueError('invalid_rng_draw')
        return self._draft(**prepared,draw=draw)

    def preflight_update(self,selection):
        selection.validate()
        decision=selection.decision
        reward=self.learner.reward(selection.state_before,decision.action)
        value=decision.score + selection.record['alpha']*(reward-decision.score)
        if not number(reward) or not number(value):
            raise ValueError('invalid_q_update')


def summary(record):
    action=record['selected_action']
    candidate=record['candidates'][action]
    result={k:record[k] for k in ('model','model_version','decision_id','state_key','selected_action','selection_mode',
                                'policy_basis','eligible_actions','epsilon','fallback_reason')}
    result.update(constraint_reasons={a:record['candidates'][a]['constraint_reasons'] for a in ACTIONS},
                  q_value=candidate['q_value'],decision_utility=candidate['decision_utility'])
    if len(compact(result))>2048:
        raise ValueError('invalid_decision_event')
    return result
