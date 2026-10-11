"""I29: the disposable Evaluation fixture builder is bounded and honest."""
import json

import pytest

from development.evaluation.paths import EvaluationRoot
from development.evaluation.reader import EvaluationReader
from tests.dashboard.evaluation_fixture import CASES, build


def _reader(destination):
    return EvaluationReader(EvaluationRoot.create(destination))


def test_fixture_disposable_and_bounded(tmp_path):
    # Non-empty or state-like destinations are refused.
    busy = tmp_path / 'busy'
    busy.mkdir()
    (busy / 'file.txt').write_text('x')
    with pytest.raises(ValueError):
        build(busy, 'empty')
    home_like = tmp_path / 'home'
    home_like.mkdir()
    (home_like / 'memory.sqlite3').write_bytes(b'')
    with pytest.raises(ValueError):
        build(home_like, 'empty')
    with pytest.raises(ValueError):
        build(tmp_path / 'x', 'nope')

    for case in CASES:
        destination = tmp_path / case
        destination.mkdir()
        meta = build(destination, case)
        assert meta['case'] == case
        reader = _reader(destination)
        if case == 'empty':
            assert reader.runs().events == ()
        elif case == 'complete-negative':
            detail = reader.detail(meta['runs'][0])
            metrics = json.loads(detail.summary.body)
            assert metrics['status'] == 'COMPLETED'
            stored = (destination / '.seed-evaluation' / 'evaluation'
                      / 'runs' / meta['runs'][0] / 'metrics.json')
            findings = json.loads(stored.read_text())['findings']
            assert findings[0]['status'] == 'NEGATIVE', findings
            assert findings[0]['execution'] == 'COMPLETED'
        elif case == 'partial':
            stored = (destination / '.seed-evaluation' / 'evaluation'
                      / 'runs' / meta['runs'][0] / 'metrics.json')
            findings = json.loads(stored.read_text())['findings']
            assert findings[0]['status'] == 'INCONCLUSIVE'
        elif case == 'missing-receipt':
            with pytest.raises(Exception):
                reader.detail(meta['runs'][0])
        elif case == 'malformed':
            with pytest.raises(Exception):
                reader.detail(meta['runs'][0])
        elif case == 'max-ids':
            page = reader.events(meta['runs'][0])
            body = json.loads(page.events[0].body)
            assert body['preupdate']['evidence']['selected_action']
            stored = (destination / '.seed-evaluation' / 'evaluation'
                      / 'runs' / meta['runs'][0] / 'events.ndjson')
            assert b'9223372036854775807' in stored.read_bytes()
        elif case == 'incompatible-plans':
            assert len(meta['runs']) == 2
            manifests = []
            for run in meta['runs']:
                path = (destination / '.seed-evaluation' / 'evaluation'
                        / 'runs' / run / 'manifest.json')
                manifests.append(json.loads(path.read_text()))
            assert manifests[0]['plan_digest'] != manifests[1]['plan_digest']
            assert manifests[0]['experiment'] != manifests[1]['experiment']
        elif case == 'max-inventory':
            first = reader.runs(limit=20)
            assert len(first.events) == 20
            assert first.cursor is not None
            second = reader.runs(first.cursor, 20)
            assert len(second.events) == 1
            assert second.cursor is None
        elif case == 'truth-annotations':
            stored = (destination / '.seed-evaluation' / 'evaluation'
                      / 'runs' / meta['runs'][0] / 'truth.json')
            assert b'TRUTH_ANNOTATION_FIXTURE' in stored.read_bytes()
