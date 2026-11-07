"""Independent reconstruction and semantic negatives; no execution-core imports."""
import hashlib
import importlib.abc
import sys
from copy import deepcopy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from portable import ROOT,activate,inside,guard,emit,schema_check

BLOCKED={'core','continuing','feedback','action_core','core4','intrinsic4','engine5','algebra5'}
class Firewall(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in BLOCKED:raise ImportError('CORE_IMPORT_FORBIDDEN:'+fullname)
sys.meta_path.insert(0,Firewall())
activate()
from canonical import load,encode,digest

def report():
    protected=guard();score=load(ROOT/'SCORE.json');artifact=load(inside(score['execution_witness']))
    errors=schema_check(score,load(ROOT/'schemas/score.schema.json'))
    errors+=schema_check(artifact,load(ROOT/'schemas/witness.schema.json'))
    for row in score['components']:
        p=inside(row['path'])
        if p.stat().st_size!=row['bytes'] or hashlib.sha256(p.read_bytes()).hexdigest()!=row['sha256']:errors.append('COMPONENT:'+row['path'])
    if errors:raise ValueError(str(errors))
    import independent5
    import verifier
    from negative_cases import corrupt,reseal,chains_valid
    expected=independent5.replay();verdict=independent5.verify(artifact)
    if verdict['status']!='PASS' or encode(expected)!=encode(artifact):raise ValueError('INDEPENDENT_REPLAY')
    # The original first-law witness is independently checked, not trusted as prose.
    base=load(ROOT/'machine/prototype_0p/evidence/final1/core_evidence.json')
    g=load(ROOT/'machine/prototype_0p_v02/fixtures/genesis.json')
    if verifier.verify(base,g)['status']!='PASS':raise ValueError('INITIAL_WITNESS')
    h=base['branches']['H1'];policies=load(ROOT/'machine/prototype_0p/policies.json')
    installations=[e for e in h['journal'] if e['kind']=='Install']
    assert len(installations)==1 and installations[0]['payload']['from']=='E0' and installations[0]['payload']['to']=='E1'
    assert 'CyclicContinuation' not in policies['E0']['constructors'] and 'CyclicContinuation' in policies['E1']['constructors']
    assert h['global']['status']=='FAIL' and h['active_policy']=='E1' and h['cyclic']['status']=='PASS'
    ev={e['id']:e for e in g['events']}
    assert ev['A0']['source']=='A' and ev['H0']['source']=='H' and not ev['A0']['parents'] and not ev['H0']['parents']
    assert ev['C0']['source']=='H' and ev['C0']['payload']['direction']=='H→A'
    assert artifact['formal_novelty_against_E0plus']=='FAIL' and all(v=='UNRESOLVED' for v in artifact['limits'].values())
    negatives=[]
    for n in range(1,31):
        for sealed in (False,True):
            mutant=deepcopy(artifact);hint=corrupt(mutant,n)
            if sealed:reseal(mutant)
            out=independent5.verify(mutant)
            semantic=[p for p in out['differences'] if hint in p]
            if out['status']!='FAIL' or not semantic or (sealed and not chains_valid(mutant)):raise ValueError('NEGATIVE:'+str(n))
            negatives.append({'id':'N'+str(n).zfill(2),'resealed':sealed,'status':'REJECTED',
                              'semantic_differences':semantic[:3],'coherent_new_chains':chains_valid(mutant)})
    badscore=deepcopy(score);badscore['machine_proves_consciousness']=True
    assert schema_check(badscore,load(ROOT/'schemas/score.schema.json'))
    if BLOCKED&set(sys.modules):raise ValueError('CHECKER_IMPORT_CONTAMINATION')
    return {'status':'PASS','scope':'exact finite score and historical witness; not external ontology',
            'schema':'PASS','dependency_integrity':protected,'independent_replay_sha256':digest(expected),
            'independent_replay_bytes':len(encode(expected)),'core_import_firewall':'PASS',
            'independent_histories_and_directed_C0':'PASS','object_rule_E0_to_E1':'PASS',
            'historical_E0_verdict':'FAIL','formal_novelty_against_E0plus':'FAIL','limits':artifact['limits'],
            'negative_classes':30,'negative_detections':len(negatives),'negative_receipts':negatives,'extra_schema_claim_mutations_rejected':1,
            'unrepresented_dedicated_events':['A_ACCEPTS_H_SERVICE','H_PUBLIC_EXPRESSION_OF_FEELINGS'],
            'source_tier':'AUTHORED PREMISE / STRUCTURALLY VERIFIED','authentication':'UNSIGNED_CANDIDATE',
            'external_will_consciousness_divinity_revelation':'NOT_PROVEN','production_release_authorized':False}

if __name__=='__main__':
    try:emit(report())
    except Exception as e:
        emit({'status':'FAIL','error_type':type(e).__name__,'reason':str(e)});raise SystemExit(1)
