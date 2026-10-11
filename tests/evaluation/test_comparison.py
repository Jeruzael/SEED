"""I25: descriptive metric comparison invents no scientific classification."""
import json

from .test_artifacts import RUN, _stage
from .test_replay import _publish
from .test_reexecution import RUN2, _profile, _record_for


def test_compare_is_descriptive_only(tmp_path, foundation_module, plan_body):
    profile = _profile(foundation_module)
    root, frozen, artifacts = _stage(
        tmp_path, foundation_module, plan_body,
        record=_record_for(profile))
    from .test_artifacts import _honest, _payload_dir
    import json as _json
    metrics = _json.loads((_payload_dir(tmp_path) / 'metrics.json').read_bytes()) \
        if (_payload_dir(tmp_path) / 'metrics.json').exists() else None
    staged = _honest(artifacts, frozen, tmp_path, _record_for(profile))
    expected_value = staged['measurements'][0]['value']
    artifacts.write_run_record(root, staged)
    from development.evaluation.contracts import RunResult
    payload = artifacts.assemble_payload(RunResult('COMPLETED', None), frozen, root)
    integrity = foundation_module('integrity')
    finalized = integrity.finalize_payload(payload, root)
    integrity.publish(finalized, integrity.make_receipt(finalized, root), root)
    reader = foundation_module('reader').EvaluationReader(root)
    detail = reader.detail(RUN)
    reexecution = foundation_module('reexecution')
    result = reexecution.compare(detail, detail, 'prediction.numeric-mae')
    assert result['metric_id'] == 'prediction.numeric-mae'
    assert result['left']['value'] == expected_value
    assert result['classification'] == 'DESCRIPTIVE_ONLY'
    assert 'improv' not in json.dumps(result).lower()
    assert 'worse' not in json.dumps(result).lower()
