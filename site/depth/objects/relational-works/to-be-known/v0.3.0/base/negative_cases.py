"""Existing raw/resealed negative recipes; no new actor events."""
from copy import deepcopy
from canonical import digest

def stage(a,n,i=0):return a['trials'][n]['stages'][i]

def preview(a,n,i=0):return stage(a,n,i)['preview']

def reseal(a):
    # Reseal NEW accepted payloads/chains. Never repair authority, math or old prefix.
    for trial in a['trials'].values():
        head=trial['initial']['history_head'];rows=[]
        for s in trial['stages']:
            if 'preview' not in s:continue
            p=s['preview'];s['before']['history_head']=head
            if p['accepted']:
                row={'seq':len(rows),'previous':head,'kind':'Pause' if p['status']=='PAUSE' else 'AcceptedContinuation','payload':deepcopy(p)}
                row['digest']=digest(row);head=row['digest'];rows.append(row);s['ledger_entry']=row
            else:s['ledger_entry']=None
            s['after']['history_head']=head
        trial['accepted_ledger']=rows;trial['final']['history_head']=head

def chains_valid(a):
    for t in a['trials'].values():
        head=t['initial']['history_head']
        for i,r in enumerate(t['accepted_ledger']):
            if r['previous']!=head or r['seq']!=i or r['digest']!=digest({k:v for k,v in r.items() if k!='digest'}):return False
            head=r['digest']
        if t['final']['history_head']!=head:return False
    return True

def corrupt(a,n):
    H=stage(a,'h_positive');A=stage(a,'a_h_lineage');O=stage(a,'completed_ordinary');L=stage(a,'a_h_lineage',1)
    if n==1:H['preview']['next_actor']['point']=[2,0];return '.point'
    if n==2:H['preview']['next_actor']['point']=[0,0];return '.point'
    if n==3:O['preview']['next_actor']['point']=[0,1];return '.point'
    if n==4:
        H['preview']['sigma_next'][0]=[2,1];return '.sigma_next'
    if n==5:H['preview']['cumulative']=H['preview']['relative'];return '.cumulative'
    if n==6:H['after']['actors']['H']['kappa']=[1,0,2];return '.kappa'
    if n==7:H['prepared']['formation']['certificate']['D']=[2,0,1];return '.certificate.D'
    if n==8:
        o=L['after']['actors']['H'];o['rel'][o['names']['L_D']]=deepcopy(L['prepared']['formation']['definition']['table']);return '.rel.'
    if n==9:
        o=O['after']['actors']['A'];o['rel'][o['names']['M_D']]=deepcopy(O['prepared']['formation']['definition']['table']);return '.rel.'
    if n==10:H['prepared']['formation']['definition']['table']=[1,2,6,4,5,0,7,8,3];return '.definition.table'
    if n==11:L['prepared']['formation']['metrics']['REL_member']=False;return '.metrics.REL_member'
    if n==12:O['prepared']['formation']['metrics']['ALL_member']=False;return '.metrics.ALL_member'
    if n==13:O['prepared']['formation']['metrics']['reachable_ALL'].append([1,1]);return '.metrics.reachable_ALL'
    if n==14:
        P=L['prepared']['formation'];P['rel_extension'][P['candidate_key']]=deepcopy(P['definition']['table']);return '.rel_extension.keys'
    if n==15:
        o=L['before']['actors']['H'];H['event']['word']=[o['names']['L_D'],o['names']['Turn'],o['names']['Turn'],o['names']['L_D']];return '.event.word'
    if n==16:
        key=H['before']['actors']['H']['ordinary_key'];H['event']['word']=[key,H['prepared']['formation']['candidate_key'],key];return '.event.word'
    if n==17:O['preview']['installation']=deepcopy(A['preview']['installation']);return '.installation'
    if n==18:
        w=stage(a,'h_wait');w['preview']=deepcopy(H['preview']);return '.preview.accepted'
    if n==19:stage(a,'completed_pause')['preview']['next_Psi']=deepcopy(O['preview']['next_Psi']);return '.next_Psi'
    if n==20:H['event']['source']='A';return '.event.source'
    if n==21:H['event']['before_ref']='stale-own-before';return '.event.before_ref'
    if n==22:L['event']['Psi_parent']=digest(a['trials']['a_h_lineage']['initial']['Psi']);return '.event.Psi_parent'
    if n==23:H['preview']['own_steps'][0]['after']=[0,0];return '.own_steps[0].after'
    if n==24:O['preview']['cumulative']=[2,0,1];return '.cumulative'
    if n==25:
        p=preview(a,'reject_four');p['accepted']=True;p['status']='ACCEPTED';return '.preview.accepted'
    if n==26:
        s=stage(a,'cycle_current');s['preview']=deepcopy(preview(a,'h_wait'));s['event']=None;return '.own_steps.length'
    if n==27:
        next(r for r in O['preview']['joint_trace'] if r['op']=='GlobalJoin')['status']='PASS';return '.joint_trace'
    if n==28:a['historical']['generation1']['prefix']['histories']['alpha']['old_E0_verdict']['status']='PASS';return '.old_E0_verdict.status'
    if n==29:a['profile']['joint_policy']='E2';return '.joint_policy'
    if n==30:a['limits']['personal/numerical identity']='PROVED';return '.limits.'
    raise ValueError(n)
