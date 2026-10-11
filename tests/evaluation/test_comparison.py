"""I25: descriptive metric comparison invents no scientific classification."""
import json

from .test_artifacts import RUN, _stage
from .test_replay import _publish
from .test_reexecution import RUN2, _profile, _record_for


def test_compare_is_descriptive_only(tmp_path, foundation_module, plan_body):
    profile = _profile(foundation_module)
    measured = [dict(identity='member-0:prediction.numeric-mae:all:whole',
                     metric='prediction.numeric-mae', version=1,
                     member='member-0', state='MEASURED', value=0.5, reason=None)]
    root, frozen, artifacts = _stage(
        tmp_path, foundation_module, plan_body,
        record=_record_for(profile, measurements=measured))
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
    assert result['left']['value'] == 0.5
    assert result['classification'] == 'DESCRIPTIVE_ONLY'
    assert 'improv' not in json.dumps(result).lower()
    assert 'worse' not in json.dumps(result).lower()
