"""Owner-attributed notes and deterministic counts, not a conversational model."""
import json
import math
import time
from pathlib import Path

from seed.telemetry import audit, emit
from .read_store import ReadStore, ServiceError


class InteractionService:
    def __init__(self, home: Path):
        self.store = ReadStore(Path(home).absolute())

    def note(self, text: str, important: bool = False) -> dict:
        if not isinstance(text, str) or not 1 <= len(text.strip()) <= 4000:
            raise ServiceError('invalid_note', 'A note must contain 1–4000 characters.')
        if type(important) is not bool:
            raise ServiceError('invalid_annotation', 'Importance must be a boolean.')
        text = text.strip()
        with self.store.connection(write=True) as db:
            cursor = db.execute(
                'INSERT INTO episodes(ts,event,state_json,note) VALUES(?,?,?,?)',
                (time.time(), 'owner', json.dumps({'source': 'owner'}), text),
            )
            episode_id = cursor.lastrowid
            db.execute('INSERT INTO annotations VALUES(?,?,?)', (episode_id, int(important), '[]'))
            emit(db, 'OWNER', 'interaction', 'Owner observation recorded', {'episode_id': episode_id})
            audit(db, 'owner_note', {'episode_id': episode_id, 'characters': len(text),
                                   'important': important}, {'status': 'complete'})
        return {'id': episode_id, 'source': 'owner', 'important': important}

    def annotate(self, episode_id: int, important: bool, tags: list[str]) -> dict:
        if (type(episode_id) is not int or not 1 <= episode_id <= 2**63 - 1
                or type(important) is not bool):
            raise ServiceError('invalid_annotation', 'Invalid episode or importance value.')
        if (not isinstance(tags, list) or len(tags) > 10 or
                any(not isinstance(tag, str) or not 1 <= len(tag.strip()) <= 32 for tag in tags)):
            raise ServiceError('invalid_annotation', 'Use at most ten tags of 1–32 characters each.')
        tags = list(dict.fromkeys(tag.strip() for tag in tags))
        with self.store.connection(write=True) as db:
            db.execute('BEGIN IMMEDIATE')
            if not db.execute('SELECT 1 FROM episodes WHERE id=?', (episode_id,)).fetchone():
                raise ServiceError('not_found', 'Episode does not exist.', 404)
            db.execute('''INSERT INTO annotations VALUES(?,?,?) ON CONFLICT(episode_id)
                       DO UPDATE SET important=excluded.important,tags_json=excluded.tags_json''',
                       (episode_id, int(important), json.dumps(tags)))
            result = {'id': episode_id, 'important': important, 'tags': tags}
            audit(db, 'episode_annotated', result, {'status': 'complete'})
            emit(db, 'OWNER', 'interaction', 'Owner annotated an episode', result)
        return result

    def summary(self, since: float) -> dict:
        until = time.time()
        if type(since) not in (int, float) or not math.isfinite(since) or not 0 <= since <= until:
            raise ServiceError('invalid_interval', 'Summary start must be a finite past timestamp.')
        with self.store.connection() as db:
            rows = db.execute('SELECT event,COUNT(*) FROM episodes WHERE ts>=? AND ts<=? GROUP BY event',
                              (since, until)).fetchall()
            counts = dict(rows)
            first, last = db.execute('SELECT MIN(ts),MAX(ts) FROM episodes').fetchone()
        return {
            'since': since, 'until': until, 'observations': counts.get('experience', 0),
            'owner_notes': counts.get('owner', 0), 'wake_records': counts.get('wake', 0),
            'sleep_stop_records': counts.get('sleep', 0), 'event_counts': counts,
            'coverage': {'first_record_at': first, 'last_record_at': last,
                         'scope': 'Retained episodes only; wake records include inferred resumes, '
                                  'and sleep records include process stops.'},
        }
