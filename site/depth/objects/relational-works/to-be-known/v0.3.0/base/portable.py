"""Package-local IO and byte guards ONLY. No domain mathematics or actor choice."""
import hashlib
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
MACHINE=ROOT/'machine'
LAYERS=('prototype_0p','prototype_0p_v02','prototype_0p_v03','prototype_0p_v03a','prototype_0p_v04','prototype_0p_v05')

def activate():
    for name in LAYERS:
        p=str(MACHINE/name)
        if p not in sys.path:sys.path.insert(0,p)
    if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))

def inside(name):
    p=ROOT/name
    if not isinstance(name,str) or not name or Path(name).is_absolute() or '..' in Path(name).parts or p.is_symlink():
        raise ValueError('UNSAFE_PACKAGE_PATH')
    p=p.resolve()
    if ROOT not in p.parents:raise ValueError('OUTSIDE_PACKAGE')
    return p

def guard():
    # Replaces PRIVATE-corpus IO guards, not any calculation/admission rule.
    # The release manifest separately pins this guard and the adapter bytes.
    activate()
    from canonical import load
    bindings=load(ROOT/'RUNTIME_BINDINGS.json')
    for n,row in bindings['files'].items():
        p=inside(n)
        if not p.is_file() or p.stat().st_size!=row['bytes'] or hashlib.sha256(p.read_bytes()).hexdigest()!=row['sha256']:
            raise ValueError('PACKAGE_INPUT_BYTES:'+n)
    return {'status':'PASS','files':len(bindings['files']),'changed':[],
            'scope':'packaged execution dependencies ONLY; not private research corpus'}

def emit(value):
    activate()
    from canonical import encode
    sys.stdout.buffer.write(encode(value))

def schema_check(value,schema,path='$'):
    """Local evaluator for the documented closed subset used in this package."""
    errors=[]
    if 'const' in schema and (type(value)!=type(schema['const']) or value!=schema['const']):errors.append(path+':const')
    if 'enum' in schema and value not in schema['enum']:errors.append(path+':enum')
    typ=schema.get('type');types={'object':dict,'array':list,'string':str,'integer':int,'boolean':bool,'null':type(None)}
    if typ and type(value)!=types[typ]:return errors+[path+':type']
    if type(value) is dict:
        props=schema.get('properties',{})
        for key in schema.get('required',[]):
            if key not in value:errors.append(path+'.'+key+':missing')
        if schema.get('additionalProperties') is False:
            errors.extend(path+'.'+k+':extra' for k in value if k not in props)
        for k,v in value.items():
            if k in props:errors.extend(schema_check(v,props[k],path+'.'+k))
    if type(value) is list:
        if 'minItems' in schema and len(value)<schema['minItems']:errors.append(path+':minItems')
        if 'maxItems' in schema and len(value)>schema['maxItems']:errors.append(path+':maxItems')
        for i,v in enumerate(value):errors.extend(schema_check(v,schema.get('items',{}),path+'['+str(i)+']'))
    if type(value) is str:
        import re
        if 'pattern' in schema and not re.search(schema['pattern'],value):errors.append(path+':pattern')
    if type(value) is int and 'minimum' in schema and value<schema['minimum']:errors.append(path+':minimum')
    return errors
