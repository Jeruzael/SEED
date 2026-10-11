"""I22: canonical scientific projection and digest."""
import json
import sqlite3

import pytest

from .test_artifacts import RUN, _payload_dir, _record, _stage

RUN2 = 'b' * 32


def _producer_db(path):
    import seed.memory as producer
    from seed import migrations
    db = sqlite3.connect(path)
    db.executescript(producer.SCHEMA)
    migrations.migrate(db)
    return db


def test_all_tables_and_sequences_in_science(tmp_path, foundation_module):
    science = foundation_module('science')
    db = _producer_db(tmp_path / 'state.sqlite3')
    db.execute("INSERT INTO meta (key, value) VALUES ('k', '1')")
    db.commit()
    projection = science.project_state(db)
    names = [t['name'] for t in projection['tables']]
    assert names == sorted(names)
    assert 'sqlite_sequence' in names
    meta = next(t for t in projection['tables'] if t['name'] == 'meta')
    assert meta['columns'][0]['name'] == 'key'
    assert ['k', '1'] in meta['rows']
    db.execute('CREATE TABLE rogue (id INTEGER)')
    with pytest.raises(Exception):
        science.project_state(db)
    db.close()


def test_exact_incidental_projection(tmp_path, foundation_module):
    science = foundation_module('science')
    db = _producer_db(tmp_path / 'state.sqlite3')
    db.execute("INSERT INTO meta (key, value) VALUES ('runtime', ?)",
               (json.dumps(dict(pid=4242, mode='x',
                                storage=dict(page_size=4096, page_count=9,
                                             logical_allocated_bytes=12))),))
    db.commit()
    projection = science.project_state(db)
    meta = next(t for t in projection['tables'] if t['name'] == 'meta')
    cell = meta['rows'][0][1]
    assert cell['pid'] == 'incidental_pid'
    assert cell['mode'] == 'x'
    assert cell['storage'] == dict(page_size='incidental_storage',
                                   page_count='incidental_storage',
                                   logical_allocated_bytes='incidental_storage')
    db.close()


def _assembled(tmp_path, foundation_module, plan_body, run_id=RUN, record=None):
    root, frozen, artifacts = _stage(tmp_path, foundation_module, plan_body,
                                     record=record)
    if run_id != RUN:
        pass
    from development.evaluation.contracts import RunResult
    payload = artifacts.assemble_payload(RunResult('COMPLETED', None), frozen, root)
    return root, payload, artifacts


def test_science_digest_cases(tmp_path, foundation_module, plan_body):
    science = foundation_module('science')
    root, payload, _ = _assembled(tmp_path, foundation_module, plan_body)
    digest1 = science.science_digest(payload, root)
    assert len(digest1) == 64
    # Recomputation is deterministic and streaming-bounded.
    assert science.science_digest(payload, root) == digest1
    chunks = list(science.iter_science(payload, root))
    assert len(chunks) >= 2
    # Operational prose is incidental: changing it must not change science.
    ops = _payload_dir(tmp_path) / 'operations.ndjson'
    ops.write_bytes(b'{"code":"run_completed","note":"different prose"}\n')
    assert science.science_digest(payload, root) == digest1
    # A changed scientific outcome (joined post-ACK body) changes the digest.
    events = _payload_dir(tmp_path) / 'events.ndjson'
    lines = events.read_bytes().splitlines()
    record = json.loads(lines[0])
    record['body']['update'] = dict(kind='b1_transition', source_ids=['changed'])
    events.write_bytes(json.dumps(record).encode() + b'\n')
    assert science.science_digest(payload, root) != digest1


def test_science_digest_incidental_run_id(tmp_path, foundation_module, plan_body):
    # Identical scientific content under a different storage run ID digests
    # identically (run IDs are incidental to science).
    import shutil
    science = foundation_module('science')
    root, payload, artifacts = _assembled(tmp_path, foundation_module, plan_body)
    digest1 = science.science_digest(payload, root)
    base = tmp_path / '.seed-evaluation' / 'evaluation' / 'partials'
    shutil.copytree(base / RUN, base / RUN2)
    rec = json.loads((base / f'{RUN}.record.json').read_bytes())
    rec['run_id'] = RUN2
    (base / f'{RUN2}.record.json').write_bytes(json.dumps(rec).encode())
    from development.evaluation.contracts import Payload
    assert science.science_digest(Payload(RUN2, payload.byte_length), root) == digest1


def test_science_order_and_key_binding(tmp_path, foundation_module, plan_body):
    # Review m3/m4: science must bind events to frames by tuple AND digest,
    # refuse duplicate journal tuples, and be sensitive to stored order.
    from development.evaluation.contracts import ContractError, RunResult
    root, frozen, artifacts = _stage(tmp_path, foundation_module, plan_body,
                                     journal_frames=2)
    record = _record(events=[
        dict(key=['measured', 'default', 1, 'update'], body=dict(confirmed=True)),
        dict(key=['measured', 'default', 2, 'update'], body=dict(confirmed=True))],
        planned_transitions=2)
    from .test_artifacts import _honest
    artifacts.write_run_record(root, _honest(artifacts, frozen, tmp_path, record))
    payload = artifacts.assemble_payload(RunResult('COMPLETED', None), frozen, root)
    science = foundation_module('science')
    digest1 = science.science_digest(payload, root)
    journal = _payload_dir(tmp_path) / 'preupdate.ndjson'
    lines = journal.read_bytes().splitlines(keepends=True)
    journal.write_bytes(b''.join(reversed(lines)))
    assert science.science_digest(payload, root) != digest1
    journal.write_bytes(b''.join(lines))
    # An event whose key tuple disagrees with its referenced frame is refused.
    events = _payload_dir(tmp_path) / 'events.ndjson'
    rows = [json.loads(x) for x in events.read_bytes().splitlines()]
    rows[0]['key'] = ['measured', 'default', 9, 'update']
    events.write_bytes(b''.join(json.dumps(r).encode() + b'\n' for r in rows))
    with pytest.raises(ContractError):
        science.science_digest(payload, root)
