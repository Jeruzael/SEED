"""Core-owned, session-bound action queue. Interrupted commands are never retried."""
import json
import time
from .telemetry import audit, emit


class CommandQueue:
    def __init__(self, memory):
        self.memory = memory

    def recover(self, session_id):
        with self.memory._lock, self.memory.db:
            self.memory.db.execute("UPDATE commands SET status='interrupted',result_json=? WHERE status='running' AND session_id!=?",
                                   (json.dumps({'error':'Previous process stopped during this request; review required.'}), session_id))
            self.memory.db.execute("UPDATE commands SET status='expired' WHERE status='pending' AND session_id!=?", (session_id,))

    def claim(self, session_id):
        with self.memory._lock:
            db = self.memory.db
            db.execute('BEGIN IMMEDIATE')
            try:
                db.execute("UPDATE commands SET status='expired' WHERE status='pending' AND expires_at<=?", (time.time(),))
                row = db.execute("SELECT * FROM commands WHERE status='pending' AND session_id=? AND expires_at>? ORDER BY created_at LIMIT 1",
                                 (session_id, time.time())).fetchone()
                if row:
                    db.execute("UPDATE commands SET status='running' WHERE id=? AND status='pending'", (row['id'],))
                db.commit()
                return dict(row) if row else None
            except BaseException:
                db.rollback()
                raise

    def finish(self, command_id, status, result):
        with self.memory._lock, self.memory.db:
            self.memory.db.execute('UPDATE commands SET status=?,result_json=? WHERE id=?',
                                   (status, json.dumps(result, allow_nan=False), command_id))
            audit(self.memory.db, 'command_result', {'id':command_id}, {'status':status, **result})
            emit(self.memory.db, 'OWNER' if status == 'complete' else 'ERROR', 'command_broker',
                 'Owner command ' + status, {'id':command_id, **result})

    def complete(self, command_id, result): self.finish(command_id, 'complete', result)
    def fail(self, command_id, reason): self.finish(command_id, 'failed', {'error':reason})
