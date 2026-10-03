import json
import subprocess
import sys
import pytest


def test_closed_message_limits(foundation_module):
    c = foundation_module('contracts')
    assert c.decode_message(b'{}' + b' ' * (65536 - 2), 'observation') == {}
    with pytest.raises(c.ContractError):
        c.decode_message(b'{}' + b' ' * (65537 - 2), 'observation')
    c.validate_json([[[[[[[[[[[[[[[[0]]]]]]]]]]]]]]]])
    with pytest.raises(c.ContractError):
        c.validate_json([[[[[[[[[[[[[[[[[0]]]]]]]]]]]]]]]]])
    c.validate_json([0] * 4096)
    with pytest.raises(c.ContractError):
        c.validate_json([0] * 4097)
    for raw in [b'{"load_ratio":0,"load_ratio":1}', b'{"truth":1}', b'{"load_ratio":NaN}',
                b'{"charging":1}', b'{"load_ratio":null}', b'{"disk_free_pct":101}',
                b'{"local_hour":true}', b'{"local_hour":24}', b'{"wall_time":1}', b'{"network":"yes"}']:
        with pytest.raises(c.ContractError):
            c.decode_message(raw, 'observation')
    assert c.decode_message(b'{"battery_pct":null,"charging":null,"network":false}', 'observation') == {
        'battery_pct': None, 'charging': None, 'network': False}
    assert c.decode_message(b'{"load_ratio":2,"disk_free_pct":0,"local_hour":23}', 'observation')['load_ratio'] == 2
    for bad in [float('inf'), 2**256, -2**256 - 1, 'x' * 4097, object()]:
        with pytest.raises(c.ContractError):
            c.validate_json(bad)


def test_public_types_exclude_truth(foundation_module):
    c = foundation_module('contracts')
    for field in ('truth', 'score', 'expected_result', 'config', 'findings', 'analysis_plan', 'evaluator_root'):
        with pytest.raises(c.ContractError):
            c.decode_message(json.dumps({field: 'sentinel'}).encode(), 'observation')
    for op in ('truth', 'score', '__dict__', 'eval', 'reset_config'):
        with pytest.raises(c.ContractError):
            c.decode_message(b'{}', op)
    assert c.decode_message(b'{"actions":["observe","reflect","consolidate","rest"]}', 'action_catalog')['actions'][3] == 'rest'
    with pytest.raises(c.ContractError):
        c.decode_message(b'{"actions":["shell"]}', 'action_catalog')
    with pytest.raises(c.ContractError):
        c.decode_message(b'{"token":"SCORE_ACK","score":1}', 'acknowledgment')


def test_registry_rejects_code(foundation_module):
    r = foundation_module('registry')
    assert r.lookup('observation', 1, kind='operation') == 'observation'
    for bad in ('os.system', '__import__("os")', '../plugin', 'shell', 'Observation'):
        with pytest.raises(ValueError):
            r.lookup(bad, 1, kind='operation')
    with pytest.raises(ValueError):
        r.lookup('observation', True, kind='operation')


def test_package_import_is_inert(foundation_module):
    foundation_module('contracts')
    script = '''
import sys
def audit(event, args):
    if event in ('socket.connect', 'subprocess.Popen', 'os.mkdir'):
        raise AssertionError('import performed work')
sys.addaudithook(audit)
import development.evaluation.contracts
import development.evaluation.registry
assert not any(n.startswith('seed.') for n in sys.modules)
'''
    subprocess.run([sys.executable, '-c', script], check=True)
