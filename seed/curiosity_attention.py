"""Durable at-most-once budget for existing internal reflection only."""
import json
import sqlite3
import time
from .curiosity import attention_suppression
from .telemetry import emit

TRANSITION_COOLDOWN = 10
TIME_COOLDOWN = 300


def summary(row, outcome):
    return {**{key: row[key] for key in ('transition_id','score','level','prediction_surprise',
                                       'uncertainty','novelty','coverage')},
            'attention_outcome': outcome, 'provenance': 'curiosity_triggered'}


class CuriosityAttention:
    def __init__(self, memory, clock=None):
        self.memory = memory
        self.clock = clock or time.time

    def claim(self, transition_id, stop_event=None, enabled=True):
        """A committed claim consumes cooldown even if optional work is later lost."""
        db = self.memory.db
        with self.memory._lock:
            db.execute('BEGIN IMMEDIATE')
            try:
                row = db.execute('SELECT * FROM curiosity_assessments WHERE transition_id=?', (transition_id,)).fetchone()
                if row is None or row['reflection_claimed'] or not row['reflection_eligible']:
                    db.commit()
                    return False
                source = db.execute('SELECT action,state_after_json FROM transitions WHERE id=?', (transition_id,)).fetchone()
                reason = attention_suppression(row, source['action'], json.loads(source['state_after_json']))
                if not enabled:
                    reason = 'disabled_by_owner'
                if stop_event is not None and stop_event.is_set():
                    reason = 'owner_stop'
                now = self.clock()
                previous = db.execute('SELECT * FROM curiosity_runtime WHERE singleton=1').fetchone()
                if reason is None and previous is not None:
                    # Count real autonomous transitions, not ID gaps or owner episodes.
                    distance = db.execute('SELECT id FROM transitions WHERE id > ? AND id <= ? ORDER BY id LIMIT ?',
                        (previous['last_reflection_transition_id'], transition_id, TRANSITION_COOLDOWN)).fetchall()
                    if len(distance) < TRANSITION_COOLDOWN:
                        reason = 'cooldown_transitions'
                    elif now - previous['last_reflection_at'] < TIME_COOLDOWN:
                        reason = 'cooldown_time'
                if reason is not None:
                    db.execute('UPDATE curiosity_assessments SET reflection_eligible=0,suppression_reason=? WHERE transition_id=?',
                               (reason,transition_id))
                    emit(db,'CURIOSITY','curiosity','Optional reflection suppressed',
                         {**summary(row,'suppressed'),'suppression_reason':reason})
                else:
                    db.execute('UPDATE curiosity_assessments SET reflection_claimed=1,claimed_at=? WHERE transition_id=?',
                               (now,transition_id))
                    db.execute('''INSERT INTO curiosity_runtime VALUES(1,?,?) ON CONFLICT(singleton) DO UPDATE SET
                        last_reflection_transition_id=excluded.last_reflection_transition_id,
                        last_reflection_at=excluded.last_reflection_at''',(transition_id,now))
                    emit(db,'CURIOSITY','curiosity','Optional reflection claimed',summary(row,'claimed'))
                db.commit()
                return reason is None
            except BaseException:
                db.rollback()
                raise

    def execute(self, transition_id, reflect, stop_event=None, enabled=True):
        if not self.claim(transition_id, stop_event, enabled):
            return False
        if stop_event is not None and stop_event.is_set():
            self._finish(transition_id, 'suppressed', suppression='owner_stop')
            return False
        try:
            reflect()
        except sqlite3.Error:
            # Storage failures follow existing core handling; never release the claim.
            raise
        except Exception as error:
            self._finish(transition_id, 'failed', failure=f'{type(error).__name__}: {error}'[:300])
            return False
        self._finish(transition_id, 'completed')
        return True

    def _finish(self, transition_id, outcome, failure=None, suppression=None):
        with self.memory._lock, self.memory.db:
            db = self.memory.db
            db.execute('''UPDATE curiosity_assessments SET reflection_completed=?,completed_at=?,
                failure_reason=?,suppression_reason=? WHERE transition_id=?''',
                (int(outcome=='completed'),self.clock() if outcome=='completed' else None,
                 failure,suppression,transition_id))
            row = db.execute('SELECT * FROM curiosity_assessments WHERE transition_id=?',(transition_id,)).fetchone()
            emit(db,'CURIOSITY','curiosity',f'Optional reflection {outcome}',
                 {**summary(row,outcome),'failure_reason':failure,'suppression_reason':suppression})
