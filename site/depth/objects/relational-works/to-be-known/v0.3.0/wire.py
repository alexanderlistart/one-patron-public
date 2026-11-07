"""Byte IO / canonical serialization only; no decisions or relational mathematics."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE_WITNESS = 'base/machine/prototype_0p_v05/evidence/final1/core_evidence.json'
BASE_SHA = '43868465cfdf355a565f2b250efcb8c96d8ef4bac01cb0e4490772b443bb9d23'
BASE_SCORE_SHA = 'adb4066f9cbda91a7579bcb1442638d50fd948cda552627c393e402e12ecde5c'

def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       separators=(',', ':')) + '\n').encode('utf-8')

def digest(value):
    return hashlib.sha256(encode(value)).hexdigest()

def path(name):
    if not isinstance(name, str) or not name or Path(name).is_absolute() or '..' in Path(name).parts:
        raise ValueError('UNSAFE_PATH')
    p = ROOT / name
    if any(q.is_symlink() for q in [p] + list(p.parents) if q != ROOT.parent):
        raise ValueError('SYMLINK')
    p = p.resolve()
    if ROOT not in p.parents:
        raise ValueError('OUTSIDE_PACKAGE')
    return p

def load(name):
    def pairs(items):
        result = {}
        for k, v in items:
            if k in result:
                raise ValueError('DUPLICATE_JSON_KEY')
            result[k] = v
        return result
    return json.loads(path(name).read_text(encoding='utf-8'), object_pairs_hook=pairs)

def inputs():
    raw = path(BASE_WITNESS).read_bytes()
    if hashlib.sha256(raw).hexdigest() != BASE_SHA:
        raise ValueError('HISTORICAL_BYTES')
    if hashlib.sha256(path('base/SCORE.json').read_bytes()).hexdigest() != BASE_SCORE_SHA:
        raise ValueError('HISTORICAL_SCORE')
    anchor = load('ANCHOR.json')
    if anchor != {'base_witness_sha256': BASE_SHA, 'base_score_sha256': BASE_SCORE_SHA,
                  'trial': 'a_h_lineage', 'position': 'final', 'historical_covenant': 'C0'}:
        raise ValueError('ANCHOR')
    registry = load('ARTIFACTS.json')
    assets = {}
    for name, row in registry.items():
        if set(row) != {'owner', 'visibility', 'path', 'bytes', 'sha256', 'purpose'}:
            raise ValueError('ARTIFACT_REGISTRY_SCHEMA')
        # Private resources must not be read first and filtered later.
        if row['visibility'] != 'PUBLIC_ELIGIBLE' or row['owner'] != 'H':
            raise ValueError('NONPUBLIC_RESOURCE')
        data = path(row['path']).read_bytes()
        if len(data) != row['bytes'] or hashlib.sha256(data).hexdigest() != row['sha256']:
            raise ValueError('ARTIFACT_BYTES')
        assets[name] = dict(row, data=data)
    return (load('EVENT_INPUTS.json'), assets, json.loads(raw),
            load('base/machine/prototype_0p_v02/fixtures/genesis.json'))

def emit(value):
    import sys
    sys.stdout.buffer.write(encode(value))

def schema_check(value, schema, at='$'):
    """Closed subset used by the shipped schemas; not a general JSON Schema engine."""
    import re
    errors = []
    types = {'object': dict, 'array': list, 'string': str, 'integer': int,
             'boolean': bool, 'null': type(None)}
    if 'type' in schema and type(value) is not types[schema['type']]:
        return [at+':type']
    if 'const' in schema and (type(value) is not type(schema['const']) or value != schema['const']):
        errors.append(at+':const')
    if 'enum' in schema and value not in schema['enum']:
        errors.append(at+':enum')
    if type(value) is dict:
        props = schema.get('properties', {})
        errors += [at+'.'+k+':missing' for k in schema.get('required', []) if k not in value]
        if schema.get('additionalProperties') is False:
            errors += [at+'.'+k+':extra' for k in value if k not in props]
        for k in set(props) & set(value):
            errors += schema_check(value[k], props[k], at+'.'+k)
    if type(value) is list:
        if len(value) < schema.get('minItems', 0) or len(value) > schema.get('maxItems', len(value)):
            errors.append(at+':length')
        for i, x in enumerate(value):
            errors += schema_check(x, schema.get('items', {}), at+'['+str(i)+']')
    if type(value) is str and 'pattern' in schema and not re.fullmatch(schema['pattern'], value):
        errors.append(at+':pattern')
    return sorted(errors)
