"""Serialization only: shared by core and verifier, never mathematical decisions."""
import hashlib
import json
from pathlib import Path

def _pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError('duplicate JSON key: ' + key)
        out[key] = value
    return out

def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'), object_pairs_hook=_pairs,
                      parse_float=lambda _: (_ for _ in ()).throw(ValueError('floats forbidden')),
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite forbidden')))

def encode(value):
    if isinstance(value, float):
        raise ValueError('floats forbidden')
    if isinstance(value, dict):
        if not all(isinstance(k, str) for k in value):
            raise ValueError('keys must be strings')
        for item in value.values():
            encode(item)
    if isinstance(value, list):
        for item in value:
            encode(item)
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'),
                       allow_nan=False) + '\n').encode('utf-8')

def digest(value):
    return hashlib.sha256(encode(value)).hexdigest()

def write_new(path, value):
    path = Path(path)
    data = encode(value)
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError('refusing to overwrite different evidence: ' + str(path))
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as handle:
        handle.write(data)
