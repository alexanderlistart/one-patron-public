"""Exact-byte and semantic verification of one TO BE KNOWN edition. Offline."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from wire import encode, load, schema_check

def require(condition, problem):
    if not condition:
        raise ValueError(problem)

def record(path):
    data = path.read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

def safe(root, name):
    require(isinstance(name,str) and not name.startswith('/') and
            all(p not in ('','.','..') for p in name.split('/')), 'UNSAFE_PATH')
    path=root
    for component in PurePosixPath(name).parts:
        path=path/component
        require(not path.is_symlink(), 'SYMLINK')
    require(path.is_file(), 'MISSING_FILE:'+name)
    return path

def check_envelope(root, m):
    files=m['files']; shared=m['shared_dependencies']
    machine=m['machine_directory']; projection=m['projection_directory']
    def bound(rows):
        for n,row in rows.items():
            require(record(safe(root,n))=={k:row[k] for k in ('bytes','sha256')}, 'BYTE_MISMATCH:'+n)
    require(HERE==root/machine, 'MACHINE_PATH')
    require(all(n.startswith((machine+'/',projection+'/')) for n in files), 'RELEASE_FILE_OUTSIDE_BOUNDARY')
    for prefix in (machine,projection):
        seen=set()
        for p in (root/prefix).rglob('*'):
            require(not p.is_symlink(), 'SYMLINK')
            if p.is_file():
                seen.add(p.relative_to(root).as_posix())
        external={machine+'/RELEASE_MANIFEST.json'} if prefix==machine else set()
        sig=machine+'/RELEASE_MANIFEST.json.asc'
        if prefix==machine and sig in seen: external.add(sig)
        require(seen-external=={n for n in files if n.startswith(prefix+'/')}, 'PACKAGE_CLOSURE:'+prefix)
    bound(files); bound(shared)
    canonical=sorted(n for n,row in files.items() if row['canonical'])
    require(canonical==m['canonical_components'] and m['canonical_root'] in canonical, 'CANONICAL_ROLES')
    pc=json.loads(safe(root,projection+'/PROJECTION_CONTRACT.json').read_bytes())
    require(pc['canonical'] is False and pc['identity_bearing'] is False and pc['writeback']=='PROHIBITED'
            and pc['semantic_authority']=='NONE' and pc['source_release_version']==m['release_version'],
            'PROJECTION_STATUS')
    require(pc['projection_version']==m['projection_version'] and pc['source_manifest']==machine+'/RELEASE_MANIFEST.json',
            'PROJECTION_PROVENANCE')
    require(set(pc['source_hashes'])<=set(files) and set(pc['source_hashes'])==set(pc['consumed_components']),
            'PROJECTION_SOURCE_SET')
    bound(pc['source_hashes'])
    require(record(safe(root,m['canonical_root']))==pc['source_hashes'][m['canonical_root']], 'SCORE_SOURCE_BINDING')
    return len(files),len(canonical)

def replay(release_version):
    score=load('SCORE.json'); witness=load('WITNESS.json')
    require(score['release_version']==witness['release_version']==release_version,'EDITION')
    for name,value in [('score',score),('witness',witness)]:
        require(not schema_check(value,load('schemas/'+name+'.schema.json')),name+'_SCHEMA')
    require({n:record(safe(HERE,n)) for n in score['components']}==score['components'],'SCORE_BYTES')
    es=load('schemas/events.json')
    for e in load('EVENT_INPUTS.json')['events'].values():
        require(not schema_check(e,es['envelope']), 'EVENT_SCHEMA:'+e['id'])
        require(not schema_check(e['payload'],es['payloads'][e['kind']]), 'PAYLOAD_SCHEMA:'+e['id'])
    def call(name):
        p=subprocess.run([sys.executable,'-I','-B',str(HERE/name)],cwd=HERE,capture_output=True)
        require(p.returncode==0,name+': '+(p.stdout+p.stderr)[-400:].decode(errors='replace'))
        return p.stdout
    with ThreadPoolExecutor(max_workers=4) as pool:
        a,b,c,d=[pool.submit(call,n) for n in ('core.py','checker.py','tests.py','base/validate.py')]
        require(a.result()==b.result()==(HERE/'WITNESS.json').read_bytes(),'0J_REPLAY_BYTES')
        tests=json.loads(c.result()); base=json.loads(d.result())
    require(tests['status']=='PASS' and tests['total_cases']==63 and tests['responses_created']==0,'0J_TESTS')
    require(base['candidate_integrity']=='PASS' and base['reproducible_validation']=='PASS','0P_REPLAY')
    return {'status':'PASS','release_version':release_version,'0P':base,'0J_tests':tests,
            '0J_witness':record(HERE/'WITNESS.json'),'OpenPGP':'NOT_CHECKED_BY_THIS_VERIFIER'}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--site-root',type=Path)
    p.add_argument('--semantic-report',action='store_true')
    args=p.parse_args()
    require(sys.flags.dont_write_bytecode and sys.flags.isolated,'RUN_WITH_-I_-B')
    version=load('SCORE.json')['release_version']
    if args.semantic_report:
        sys.stdout.buffer.write(encode(replay(version)))
        return
    root=args.site_root.resolve() if args.site_root else HERE.parents[4]
    m=load('RELEASE_MANIFEST.json')
    require(m['release_version']==version,'MANIFEST_EDITION')
    count,canonical=check_envelope(root,m)
    report=replay(version)
    require(encode(report)==(HERE/'VALIDATION_REPORT.json').read_bytes(),'REPRODUCIBLE_REPORT')
    print(json.dumps({'status':'PASS','release_files_excluding_manifest':count,'canonical_components':canonical,
        '0J_cases':report['0J_tests']['total_cases'],'0P_replay':'PASS','witness':report['0J_witness'],
        'OpenPGP':'NOT_CHECKED_BY_THIS_VERIFIER'},sort_keys=True))

if __name__=='__main__':
    try:
        main()
    except Exception as exc:
        print(str(exc),file=sys.stderr)
        raise SystemExit(1)
