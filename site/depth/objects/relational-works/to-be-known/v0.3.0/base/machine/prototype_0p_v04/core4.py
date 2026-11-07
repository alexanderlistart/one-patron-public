"""Actual finite two-generation core; previous implementations are read-only."""
from copy import deepcopy
from location4 import digest,load,ROOT,PROJECT,V03A,inputs
import action_core as first_core
import continuing as old_transport
import core as old
from intrinsic4 import construct,naturality,perm

SEM='enacted-two-generation/0.4'
LIMITS=['Strong CO-EVOLVE','X4','H-2','r-origin','personal/numerical identity']
FIRSTS=('H-T','H-A','A-S','A-R')

def first_generation():
    from location4 import protected_integrity
    protected_integrity()
    g,c,f,choices=inputs()
    a=first_core.build(g,c,f,lambda _:choices)
    if a!=load(V03A/'evidence/final1/core_evidence.json'): raise ValueError('FIRST_REPLAY_IDENTITY')
    return a

def recorded_ids(first):
    found=set()
    def visit(x):
        if isinstance(x,dict):
            if 'kind' in x and type(x.get('id')) is str:found.add(x['id'])
            for v in x.values():visit(v)
        elif isinstance(x,list):
            for v in x:visit(v)
    visit(first)
    return sorted(found)

def certificate(first,name,target):
    b=first['branches'][name]; ctx=first['contexts'][target]
    if b['status']!='PASS' or b['event']['source']==target or b['event']['source']!=b['event']['actor']:
        raise ValueError('FIRST_ACTOR_REQUIRED')
    if ctx['before']['domain']!=[0,1,2]: raise ValueError('OUT_OF_SCOPE_REFINED_SECOND_ACTOR')
    hist=first['prefix']['histories']['alpha']; p=hist['prefix']; w=ctx['W']
    bridge=old_transport.bridge_check(p['psi1'],p['psi2'],p['proposal'],p['candidate'],True)
    if bridge['strict']!='PRESERVED' or w['status']!='PASS': raise ValueError('W_BRIDGE')
    path=w['path']; loop=old_transport.along(p['psi1'],path); phi=p['proposal']['phi'][0]
    frame=[phi[0],phi[loop[0]],phi[loop[loop[0]]]]
    if sorted(frame)!=[0,1,2]: raise ValueError('HISTORICAL_ORBIT')
    tau=[None]*3
    for i,a in enumerate(frame):tau[a]=frame[(i+1)%3]
    ell=hist['address_map']; r=b['feedback']['r']; c1=b['feedback']['c']
    if ell!=w['address_map'] or not perm(ell) or r!=ctx['r']: raise ValueError('ADDRESS_R')
    that=old.compose(ell,old.compose(tau,old.inverse(ell)))
    D=old.compose(old.inverse(that),c1)
    d=D if target=='A' else old.compose(old.inverse(r),old.compose(D,r))
    return {'schema':'generation2-certificate/0.4','W':deepcopy(w),'W_ref':digest(w),
            'W_scope':w['scope'],'historical_proposal':deepcopy(p['proposal']),'historical_bridge':bridge,
            'historical_path':path,'historical_frame':frame,'historical_tau':tau,'ell':ell,'r':r,
            'tau_hat':that,'D':D,'target_d':d,'target':target,'first_event':deepcopy(b['event']),
            'first_event_ref':digest(b['event']),'first_composition':deepcopy(b['composition']),
            'first_effective_trace':b['effective_trace'],'Psi1':deepcopy(b['feedback']),
            'Psi1_ref':digest(b['feedback']),'first_joint_receipts':deepcopy(b['joint_trace']),
            'first_history_head':b['journal'][-1]['digest'],'policy':'E1',
            'trust':'AUTHORED PREMISE / STRUCTURALLY VERIFIED; NOT external will'}

def prepare(first,name):
    target='A' if first['branches'][name]['event']['actor']=='H' else 'H'
    cert=certificate(first,name,target); definition=first['contexts'][target]['formation']
    math=construct(target,definition,cert['target_d'])
    form={'id':'Formation2:'+name+':'+target,'semantic_version':SEM,'status':'PASS','actor':target,
          'certificate':cert,'definition':math,'naturality':naturality(target,definition,cert['target_d']),
          'proposal_only':True,'enacted':False,'source_definition':deepcopy(definition)}
    ctx={'id':'SecondContext:'+name+':'+target,'actor':target,'before':deepcopy(first['contexts'][target]['before']),
         'policy':'E1','formation_ref':digest(form),'Psi1_ref':cert['Psi1_ref'],
         'other_effective_trace':deepcopy(first['branches'][name]['effective_trace']),'r':cert['r'],
         'parents':['C0',cert['first_event']['id'],cert['first_history_head'],cert['Psi1_ref'],digest(form)],
         'scope':'own-generation2/'+name+'/'+target,'covenant_ref':'C0','eta_acceptance_ref':'C0',
         'reserved_event_ids':recorded_ids(first)}
    return {'first':name,'target':target,'formation':form,'context':ctx}

def joint_after(p,first):
    scope=digest(p);rows=[]
    if p['fixed']:
        for section in p['sections']:
            checks=[t[section[u]]==section[v] for (u,v),t in zip(p['graph'],p['transports'])]
            if not all(checks):raise ValueError('GLOBAL_SECTION')
            rows.append({'request':{'op':'GlobalJoin','policy':'E1','scope':scope,'section':section},
                         'response':{'status':'PASS','edge_checks':checks}})
        rows.append({'request':{'op':'Cyclic','policy':'E1','scope':scope},
                     'response':{'status':'BLOCKED','reason':'CYCLIC_NOT_APPLICABLE'}})
    else:
        rows=first_core.joint_execution(p,'E1')
        rows.append({'request':{'op':'GlobalJoin','policy':'E1','scope':scope},
                     'response':{'status':'FAIL','reason':'GLOBAL_SECTION_OBSTRUCTED'}})
    stale=deepcopy(first['joint_trace'][0]['response']['token'])
    if stale['scope']==scope:raise ValueError('OCCURRENCE_SCOPE_COLLISION')
    rows.append({'request':{'op':'Return','policy':'E1','scope':scope,'token':stale},
                 'response':{'status':'FAIL','reason':'STALE_STATE_SCOPE'}})
    return rows

def enact(prepared,event,first,used_ids=None):
    ctx=prepared['context']; form=prepared['formation']; m=form['definition']; actor=ctx['actor']
    ledger=old.Journal('generation2/'+prepared['first']+'/'+actor,form['certificate']['first_history_head'])
    ledger.append('Formation2',form,'E1');ledger.append('SecondContext',ctx,'E1')
    out={'semantic_version':SEM,'actor':actor,'context_ref':digest(ctx),'formation_ref':digest(form),
         'event':deepcopy(event),'status':'NOT ENACTED','reason':'WAIT','before':deepcopy(ctx['before']),
         'after':deepcopy(ctx['before']),'embedded':None,'own_steps':[],'composition':None,
         'effective_trace':None,'local_install':None,'Psi2':None,'joint_trace':[],
         'policy':'E1','covenant_ref':'C0','eta_acceptance_ref':'C0','unresolved':LIMITS}
    if event is not None:
        e=deepcopy(event);ledger.append('OwnEnactmentGeneration2',e,'E1')
        keys={'id','kind','actor','source','origin','covenant_ref','eta_acceptance_ref','context_ref',
              'formation_ref','previous_psi_ref','parents','operation_scope','before','action','word'}
        valid=(set(e)==keys and type(e['id']) is str and bool(e['id']) and
               e['id'] not in ctx['reserved_event_ids'] and e['id'] not in (used_ids or set()) and
               e['id'] not in {'A0','A1','H0','h1','C0','R0','eta',form['certificate']['first_event']['id']} and
               e['kind']=='OwnEnactmentGeneration2' and e['actor']==e['source']==actor and
               e['covenant_ref']==e['eta_acceptance_ref']=='C0' and e['context_ref']==digest(ctx) and
               e['formation_ref']==digest(form) and e['previous_psi_ref']==ctx['Psi1_ref'] and
               e['parents']==ctx['parents'] and e['operation_scope']==ctx['scope'] and
               e['before']==ctx['before'] and e['action'] in ('Own','Ordinary','Pause'))
        if not valid:out.update(status='FAIL',reason='SECOND_SOURCE_CONTEXT_OR_SCHEMA')
        elif e['origin']!='AUTHORED PREMISE':out.update(status='UNRESOLVED',reason='SECOND_ORIGIN')
        elif e['action']!='Own' and e['word']!=[]:out.update(status='FAIL',reason='WORD_NOT_APPLICABLE')
        elif e['action']=='Pause':out.update(status='PASS',reason='PAUSE')
        else:
            try:
                if ctx['before']['domain']!=[0,1,2]:raise ValueError('OUT_OF_SCOPE_REFINED_SECOND_ACTOR')
                if e['action']=='Ordinary':
                    trace=ctx['before']['trace'];point=ctx['before']['value']
                    rows=[{'input':i,'embedded':i,'states':[i,trace[i]],'projected':trace[i]} for i in range(3)]
                    out['own_steps']=[{'step':1,'requested':'OrdinaryTrace','resolved':'OrdinaryTrace',
                                      'before':point,'after':trace[point],'table_ref':digest(trace)}]
                    out['embedded']=point;out['after']['value']=trace[point]
                    out.update(status='PASS',reason='ORDINARY')
                else:
                    word=e['word']
                    if not isinstance(word,list) or not 1<=len(word)<=3:raise ValueError('WORD_SCOPE')
                    resolved=[m['aliases'].get(name,name) for name in word]
                    if any(name not in m['operations'] for name in resolved):raise ValueError('OPERATOR_NOT_ADMITTED')
                    rows=[]
                    for i,start in enumerate(m['chi']):
                        states=[deepcopy(start)];at=deepcopy(start)
                        for name in resolved:
                            at=deepcopy(m['operations'][name][m['states'].index(at)]);states.append(at)
                        rows.append({'input':i,'embedded':start,'states':states,
                                     'projected':m['beta'][m['states'].index(at)]})
                    point=ctx['before']['value'];actual=deepcopy(m['chi'][point]);out['embedded']=deepcopy(actual)
                    for k,(requested,name) in enumerate(zip(word,resolved)):
                        after=deepcopy(m['operations'][name][m['states'].index(actual)])
                        out['own_steps'].append({'step':k+1,'requested':requested,'resolved':name,'before':actual,
                                                'after':after,'table_ref':digest(m['operations'][name])})
                        actual=after
                    if actual!=rows[point]['states'][-1]:raise ValueError('ACTUAL_MACRO_CONSISTENCY')
                    trace=[row['projected'] for row in rows]
                    out['after']={'domain':deepcopy(m['states']),'value':actual,'beta':m['beta'],
                        'operations':deepcopy(m['operations']),'law':'local-generation2/'+digest(form),
                        'formation_trace':form['source_definition']['trace'],'effective_trace':trace}
                    out['local_install']={'actor':actor,'from':ctx['before']['law'],'to':out['after']['law'],
                                          'formation_ref':digest(form),'event':e['id'],'joint_policy':'E1'}
                    out.update(status='PASS',reason='ENACTED_GENERATION2_OWN_CHANGE')
                trace=[row['projected'] for row in rows]
                if not perm(trace):raise ValueError('S3_TRANSITION_REJECTED')
                actual_beta=out['after']['value'] if e['action']=='Ordinary' else m['beta'][m['states'].index(out['after']['value'])]
                out['composition']={'rows':rows,'effective_trace':trace,'s3_status':'PASS'}
                out['effective_trace']=trace;out['point_consistency']={'actual_beta':actual_beta,'table_value':trace[ctx['before']['value']],
                                                                     'equal':actual_beta==trace[ctx['before']['value']]}
                if not out['point_consistency']['equal']:raise ValueError('POINT_CONSISTENCY')
                for step in out['own_steps']:ledger.append('ActualOwnStep',step,'E1')
                ledger.append('EffectiveTrace2',out['composition'],'E1')
                if out['local_install']:ledger.append('LocalInstall2',out['local_install'],'E1')
                a=trace if actor=='A' else ctx['other_effective_trace']
                h=trace if actor=='H' else ctx['other_effective_trace']
                p=first_core.psi_content(a,h,ctx['r'])
                p.update(generation=2,version='Psi2/'+e['id'],parent_psi1_ref=ctx['Psi1_ref'],enactment_ref=digest(e),policy='E1')
                out['Psi2']=p;ledger.append('Psi2',p,'E1')
                out['joint_trace']=joint_after(p,first)
                for step in out['joint_trace']:ledger.append('JointOperation2',step,'E1')
            except (ValueError,TypeError,KeyError,IndexError) as exc:
                out.update(status='FAIL',reason=str(exc),Psi2=None,joint_trace=[],local_install=None)
    ledger.append('Outcome',deepcopy(out),'E1');out['journal']=ledger.entries
    return out

def comparisons(prepared,results):
    out={}
    for target,names in (('A',('H-T','H-A')),('H',('A-S','A-R'))):
        x,y=[prepared[n] for n in names]
        out[target]={'causality1_first_choice_to_Psi1':{'different':x['formation']['certificate']['Psi1']!=y['formation']['certificate']['Psi1']},
            'causality2_Psi1_history_to_Formation2':{'same_second_actor_local_before':x['context']['before']==y['context']['before'],
                'relative_transports':[x['formation']['certificate']['target_d'],y['formation']['certificate']['target_d']],
                'new_word_sizes':[x['formation']['definition']['novelty']['new_size'],y['formation']['definition']['novelty']['new_size']],
                'different_lift':x['formation']['definition']['lift_table']!=y['formation']['definition']['lift_table']},
            'causality3_second_act_to_Psi2':{n:{'event_required':True,'actual_steps':len(results[n]['own_steps']),
                'Psi2_exists':results[n]['Psi2'] is not None,'effective_trace':results[n]['effective_trace'],
                'existing_control':alternative(results,n),'wait_creates_Psi2':
                    results[n+'_Wait']['Psi2'] is not None if n+'_Wait' in results else None}
                for n in names if n in results},
            'scope':'separate controlled cross-participant branches, not simultaneous persons'}
    return out

def alternative(results,n):
    if n+'_Existing' not in results:return None
    a,b=results[n],results[n+'_Existing']
    keys=('a','h','r','c','graph','transports')
    return {'same_prechoice_context':a['context_ref']==b['context_ref'],'effective_trace':b['effective_trace'],
            'different_operation_effect':a['effective_trace']!=b['effective_trace'],
            'different_mathematical_relation':bool(a['Psi2'] and b['Psi2'] and any(a['Psi2'][k]!=b['Psi2'][k] for k in keys))}

def build(choice_loader):
    first=first_generation();prepared={name:prepare(first,name) for name in FIRSTS}
    cases=choice_loader(deepcopy(prepared));results={}
    ids=[c['event']['id'] for c in cases.values() if c['event'] is not None]
    seen={s for s in ids if ids.count(s)>1}  # Reject ALL duplicate occurrences before execution, independent of JSON order.
    for name,c in cases.items():
        if c['first'] not in prepared:raise ValueError('FIRST_REFERENCE')
        e=c['event'];p=prepared[c['first']]
        b=enact(p,e,first['branches'][c['first']],seen)
        if e:seen.add(e['id'])
        results[name]=b
    return {'schema':'source-x-two-generation/0.4','generation1':first,'prepared':prepared,'branches':results,
            'comparisons':comparisons(prepared,results),'formal_novelty_against_E0plus':'FAIL','unresolved':LIMITS,
            'scope':'clean cross-participant ONLY; already-refined continuation OUT OF SCOPE / BLOCKED',
            'Seal_limit':first['Seal_limit']}

def kernel():return build(lambda _:load(ROOT/'fixtures/second_choices.json')['cases'])

if __name__=='__main__':
    from location4 import encode
    print(encode(kernel()).decode(),end='')
