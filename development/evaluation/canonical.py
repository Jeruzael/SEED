"""Typed canonical hash projection, independent from raw producer JSON."""
import json
from .contracts import ContractError, validate_json, strict_json


def canonical_bytes(value) -> bytes:
    validate_json(value)
    def typed(v):
        if type(v) is float:
            return {'f64': v.hex()}
        if type(v) is dict:
            if 'f64' in v or 'utf8_bytes' in v:
                raise ContractError()
            return {k: typed(x) for k, x in v.items()}
        if type(v) is list:
            return [typed(x) for x in v]
        return v
    return (json.dumps(typed(value), sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False) + '\n').encode('ascii')


def decode_canonical(raw: bytes):
    value = strict_json(raw, max_bytes=128 * 1024)
    def untyped(v):
        if type(v) is dict:
            if set(v) == {'f64'}:
                try:
                    f = float.fromhex(v['f64'])
                    if f.hex() != v['f64']:
                        raise ContractError()
                    return f
                except (ValueError, TypeError):
                    raise ContractError() from None
            return {k: untyped(x) for k, x in v.items()}
        if type(v) is list:
            return [untyped(x) for x in v]
        return v
    result = untyped(value)
    if canonical_bytes(result) != raw:
        raise ContractError()
    return result


def canonical_stream(values):
    """Yield canonical bytes per value for streaming digest construction."""
    for value in values:
        yield canonical_bytes(value)
