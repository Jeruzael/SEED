"""Structured durable events; never derive facts from terminal output."""
import json
import time

EVENT_LIMIT = 50000
AUDIT_LIMIT = 20000


def emit(db, category: str, source: str, message: str, data: dict) -> int:
    cursor = db.execute('INSERT INTO events(ts,category,source,message,data_json) VALUES(?,?,?,?,?)',
                        (time.time(), category, source, message, json.dumps(data, allow_nan=False)))
    event_id = cursor.lastrowid
    if event_id % 100 == 0:
        db.execute('DELETE FROM events WHERE id <= ?', (event_id - EVENT_LIMIT,))
    return event_id


def audit(db, action: str, parameters: dict, result: dict) -> None:
    cursor = db.execute('INSERT INTO audit(ts,action,parameters_json,result_json) VALUES(?,?,?,?)',
                       (time.time(), action, json.dumps(parameters, allow_nan=False), json.dumps(result, allow_nan=False)))
    if cursor.lastrowid % 100 == 0:
        db.execute('DELETE FROM audit WHERE id <= ?', (cursor.lastrowid - AUDIT_LIMIT,))


class Telemetry:
    def __init__(self, memory):
        self.memory = memory

    def emit(self, category, source, message, data):
        with self.memory._lock, self.memory.db:
            return emit(self.memory.db, category, source, message, data)

    def runtime(self, **fields):
        with self.memory._lock, self.memory.db:
            row = self.memory.db.execute('SELECT data_json FROM runtime WHERE singleton=1').fetchone()
            data = json.loads(row[0]) if row else {}
            data.update(fields)
            self.memory.db.execute('INSERT INTO runtime VALUES(1,?) ON CONFLICT(singleton) DO UPDATE SET data_json=excluded.data_json',
                                   (json.dumps(data, allow_nan=False),))
