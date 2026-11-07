"""Read-only candidate gate. Never signs, publishes, fetches or writes files."""
import argparse
import hashlib
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from portable import ROOT,activate,inside,emit
activate()
from canonical import load,encode

def semantic_report():
    def call(name):
        p=subprocess.run([sys.executable,'-I','-B',str(ROOT/name)],cwd=ROOT,capture_output=True)
        if p.returncode:raise ValueError('SUBPROCESS_FAILED:'+name+':'+p.stdout.decode(errors='replace')[:500])
        return p.stdout
    with ThreadPoolExecutor(max_workers=2) as pool:
        core=pool.submit(call,'execute.py');other=pool.submit(call,'independent_check.py')
        calculated=core.result();independent=__import__('json').loads(other.result())
    score=load(ROOT/'SCORE.json');witness=inside(score['execution_witness']).read_bytes()
    if calculated!=witness:raise ValueError('EXECUTION_BYTES_MISMATCH')
    h=hashlib.sha256(calculated).hexdigest()
    if independent['status']!='PASS' or independent['independent_replay_sha256']!=h:raise ValueError('REPLAY_COMPARISON')
    return {'candidate_status':'VALIDATED_UNSIGNED_CANDIDATE','work_id':score['work_id'],'candidate_version':score['candidate_version'],
            'source_score_sha256':hashlib.sha256((ROOT/'SCORE.json').read_bytes()).hexdigest(),
            'execution_replay':'PASS','execution_sha256':h,'execution_bytes':len(calculated),
            'independent':independent,'authentication':'UNSIGNED','public_release':'NOT_AUTHORIZED',
            'author_approval':'PENDING','human_projection':'CONTRACT_ONLY_NOT_BUILT'}

def inventory():
    m=load(ROOT/'RELEASE_MANIFEST.json');expected=set(m['files'])
    actual={str(p.relative_to(ROOT)) for p in ROOT.rglob('*') if p.is_file() and p!=ROOT/'RELEASE_MANIFEST.json'}
    if expected!=actual:raise ValueError('PACKAGE_INVENTORY')
    for n,row in m['files'].items():
        p=inside(n)
        if p.stat().st_size!=row['bytes'] or hashlib.sha256(p.read_bytes()).hexdigest()!=row['sha256']:raise ValueError('MANIFEST_BYTES:'+n)
    return len(expected)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--semantic-report',action='store_true');args=p.parse_args()
    try:
        count=None if args.semantic_report else inventory()
        report=semantic_report()
        if args.semantic_report:emit(report)
        else:
            if encode(report)!=(ROOT/'VALIDATION_REPORT.json').read_bytes():raise ValueError('VALIDATION_REPORT_NOT_REPRODUCED')
            emit({'candidate_integrity':'PASS','reproducible_validation':'PASS','manifest_entries':count,
                  'execution_sha256':report['execution_sha256'],'authentication':'UNSIGNED',
                  'verdict':'READY_FOR_AUTHOR_REVIEW','production_release':'NOT_AUTHORIZED'})
    except Exception as e:
        emit({'candidate_integrity':'FAIL','error_type':type(e).__name__,'reason':str(e)});raise SystemExit(1)
