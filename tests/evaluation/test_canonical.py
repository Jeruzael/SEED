import hashlib
import math
import pytest


def test_plan_digest_typed_values(foundation_module):
    c = foundation_module('canonical')
    digest = lambda v: hashlib.sha256(c.canonical_bytes(v)).hexdigest()
    assert digest(1) != digest(1.0)
    assert digest(+0.0) != digest(-0.0)
    assert c.canonical_bytes({'b': 1, 'a': .5}) == b'{"a":{"f64":"0x1.0000000000000p-1"},"b":1}\n'
    assert digest({'a': 1, 'b': 2}) == digest({'b': 2, 'a': 1})
    assert digest([1, 2]) != digest([2, 1])
    for f in [0.0, -0.0, .1, 1.0, float.fromhex('0x0.0000000000001p-1022'), 1.7976931348623157e308]:
        restored = c.decode_canonical(c.canonical_bytes(f))
        assert restored.hex() == f.hex()
    for bad in [math.nan, math.inf, {'f64': '0x1.0000000000000p+0'}, '\u00e9']:
        with pytest.raises(ValueError):
            c.canonical_bytes(bad)
    with pytest.raises(ValueError):
        c.decode_canonical(b'1\n\n')
