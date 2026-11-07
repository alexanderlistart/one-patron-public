"""Independent generation2 reconstruction; imports no v0.4 core/intrinsic math."""
from copy import deepcopy
from functools import lru_cache
import json
from location4 import digest,encode,load,ROOT,V03A,inputs
import causality_checker as preceding
import independent as old_diff

SEM='enacted-two-generation/0.4'
LIMITS=['Strong CO-EVOLVE','X4','H-2','r-origin','personal/numerical identity']
FIRSTS=('H-T','H-A','A-S','A-R')

def product(a,b):return [a[b[i]] for i in range(len(b))]
def inverse(a):return [a.index(i) for i in range(len(a))]
def permutation(p):return type(p) is list and len(p)==3 and all(type(v) is int for v in p) and set(p)=={0,1,2}

def maps(definition):
    states=definition['states'];lookup={encode(s):i for i,s in enumerate(states)}
    return {name:[lookup[encode(s)] for s in output] for name,output in definition['operations'].items()}

def semigroup(generators):
    # Saturate by right multiplication; independent of the core's left BFS.
    known={tuple(range(len(generators[0])))}
    while True:
        nxt=known|{tuple(a[g[i]] for i in range(len(g))) for a in known for g in generators}
        if nxt==known:return [list(a) for a in sorted(known)]
        known=nxt

def own_structure(actor,f,d):
    st=deepcopy(f['states']);beta=f['beta'];names=maps(f);look={encode(s):i for i,s in enumerate(st)}
    embeddings={i:look[encode(s)] for i,s in enumerate(f['embedding'])}
    t={i:beta[j] for i,j in embeddings.items()}
    if not permutation(list(t.values())):raise ValueError('section')
    sections={i:embeddings[next(k for k,v in t.items() if v==i)] for i in range(3)}
    relations={};normal=[]
    if actor=='H':
        T=names['Turn'];oldnames=['Turn','Advance'];lift='L_D';alias='Turn'
        for i,a in sections.items():
            seq=[a,T[a],T[T[a]]]
            if len(set(seq))!=3 or T[seq[-1]]!=a or any(beta[q]!=i for q in seq):raise ValueError('normal form')
            relations.update({seq[0]:seq[1],seq[1]:seq[2],seq[2]:sections[d[i]]});normal.append(seq)
        sec={'e':[st[sections[i]] for i in range(3)]}
    elif actor=='A':
        S=names['Seal'];zero={i:S[a] for i,a in sections.items()}
        oldnames=['Seal','Readdress'];lift='M_D';alias='Seal'
        for i in range(3):
            if zero[i]==sections[i] or beta[zero[i]]!=i or S[zero[i]]!=zero[i]:raise ValueError('layers')
            relations[zero[i]]=zero[i];relations[sections[i]]=zero[d[i]]
            normal.append([zero[i],sections[i]])
        sec={'e0':[st[zero[i]] for i in range(3)],'e1':[st[sections[i]] for i in range(3)]}
    else:raise ValueError('actor')
    if set(relations)!=set(range(len(st))):raise ValueError('coverage')
    indices=[relations[i] for i in range(len(st))];table=[st[j] for j in indices]
    old=semigroup([names[n] for n in oldnames]);new=semigroup([names[n] for n in oldnames]+[indices])
    operations=deepcopy(f['operations']);aliases={lift:alias} if indices==names[alias] else {}
    if not aliases:operations[lift]=table
    order=None
    if sorted(indices)==list(range(len(st))):
        for n in range(1,100):
            if all(iterate(indices,i,n)==i for i in range(len(st))):order=n;break
    return {'actor':actor,'states':st,'beta':deepcopy(beta),'chi':deepcopy(f['embedding']),
        'sections':sec,'normal_forms':[[st[j] for j in row] for row in normal],
        'lift_name':lift,'lift_table':table,'operations':operations,'aliases':aliases,
        'novelty':{'status':'ALIAS / NO NEW OWN OPERATOR' if indices in old else 'NEW OWN OPERATOR',
                   'lift_old_member':indices in old,'old_word_maps':old,'new_word_maps':new,
                   'old_size':len(old),'new_size':len(new),'order':order,'rank':len(set(indices)),
                   'idempotent':all(indices[indices[i]]==indices[i] for i in range(len(st)))},
        'source_definition_ref':digest(f),'scope':'finite own language; NOT E2'}

def iterate(mapping,x,n):
    for _ in range(n):x=mapping[x]
    return x

def covariance(actor,f,d):
    states=f['states'];n=len(states);groups={i:[j for j,b in enumerate(f['beta']) if b==i] for i in range(3)}
    patterns=[[1,2,0],[0,2,1],[2,1,0]] if actor=='H' else [[1,0],[0,1],[1,0]]
    original=own_structure(actor,f,d);left_ix=[states.index(s) for s in original['lift_table']];result=[]
    for g in ([0,1,2],[1,0,2]):
        fm={j:groups[g[i]][patterns[i][z]] for i in range(3) for z,j in enumerate(groups[i])}
        fi={v:k for k,v in fm.items()};back={v:k for k,v in enumerate(g)};new=deepcopy(f)
        new['beta']=[g[f['beta'][fi[j]]] for j in range(n)]
        new['embedding']=[states[fm[states.index(f['embedding'][back[i]])]] for i in range(3)]
        new['trace']=[new['beta'][states.index(s)] for s in new['embedding']]
        for name,t in maps(f).items():new['operations'][name]=[states[fm[t[fi[j]]]] for j in range(n)]
        dp=[g[d[back[i]]] for i in range(3)];rebuilt=own_structure(actor,new,dp)
        ix=[states.index(s) for s in rebuilt['lift_table']]
        left=[fm[j] for j in left_ix];right=[ix[fm[j]] for j in range(n)]
        if left!=right:raise ValueError('covariance')
        result.append({'g':g,'own_bijection':[fm[i] for i in range(n)],'d_prime':dp,'left':left,'right':right,'equal':True})
    return {'status':'PASS','scope':'representation isomorphism, not own historical change','cases':result}

def along(p,path):
    result=[0,1,2]
    for e in path:
        idx=p['graph'].index(e);result=product(p['transports'][idx],result)
    return result

def proof(first,name,target):
    b=first['branches'][name];ctx=first['contexts'][target];h=first['prefix']['histories']['alpha'];p=h['prefix'];w=ctx['W']
    squares=[];proposal=p['proposal']
    for (u,v),mapping in zip(p['psi1']['graph'],p['psi1']['transports']):
        path=proposal['paths'][str(u)+'-'+str(v)]
        left=product(proposal['phi'][v],mapping);right=product(along(p['psi2'],path),proposal['phi'][u])
        if left!=right:raise ValueError('historical square')
        squares.append({'edge':[u,v],'path':path,'left':left,'right':right,'commutes':True})
    bridge={'strict':'PRESERVED','historical':'PRESERVED','squares':squares}
    loop=along(p['psi1'],w['path']);phi=proposal['phi'][0]
    frame=[phi[0],phi[loop[0]],phi[loop[loop[0]]]]
    tau=[frame[(frame.index(i)+1)%3] for i in range(3)]
    ell=h['address_map'];r=b['feedback']['r'];that=product(ell,product(tau,inverse(ell)))
    D=[inverse(that)[b['feedback']['c'][i]] for i in range(3)]
    d=D if target=='A' else product(inverse(r),product(D,r))
    return {'schema':'generation2-certificate/0.4','W':deepcopy(w),'W_ref':digest(w),'W_scope':w['scope'],
        'historical_proposal':deepcopy(proposal),'historical_bridge':bridge,'historical_path':w['path'],
        'historical_frame':frame,'historical_tau':tau,'ell':ell,'r':r,'tau_hat':that,'D':D,'target_d':d,
        'target':target,'first_event':deepcopy(b['event']),'first_event_ref':digest(b['event']),
        'first_composition':deepcopy(b['composition']),'first_effective_trace':b['effective_trace'],
        'Psi1':deepcopy(b['feedback']),'Psi1_ref':digest(b['feedback']),'first_joint_receipts':deepcopy(b['joint_trace']),
        'first_history_head':b['journal'][-1]['digest'],'policy':'E1',
        'trust':'AUTHORED PREMISE / STRUCTURALLY VERIFIED; NOT external will'}

def preparation(first,name):
    actor='A' if first['branches'][name]['event']['actor']=='H' else 'H'
    cert=proof(first,name,actor);definition=first['contexts'][actor]['formation']
    form={'id':'Formation2:'+name+':'+actor,'semantic_version':SEM,'status':'PASS','actor':actor,
          'certificate':cert,'definition':own_structure(actor,definition,cert['target_d']),
          'naturality':covariance(actor,definition,cert['target_d']),'proposal_only':True,'enacted':False,
          'source_definition':deepcopy(definition)}
    ctx={'id':'SecondContext:'+name+':'+actor,'actor':actor,'before':deepcopy(first['contexts'][actor]['before']),
         'policy':'E1','formation_ref':digest(form),'Psi1_ref':cert['Psi1_ref'],
         'other_effective_trace':deepcopy(first['branches'][name]['effective_trace']),'r':cert['r'],
         'parents':['C0',cert['first_event']['id'],cert['first_history_head'],cert['Psi1_ref'],digest(form)],
         'scope':'own-generation2/'+name+'/'+actor,'covenant_ref':'C0','eta_acceptance_ref':'C0',
         'reserved_event_ids':past_ids(first)}
    return {'first':name,'target':actor,'formation':form,'context':ctx}

def past_ids(first):
    todo=[first];ids=set()
    while todo:
        x=todo.pop()
        if type(x) is dict:
            if 'kind' in x and type(x.get('id')) is str:ids.add(x['id'])
            todo.extend(x.values())
        elif type(x) is list:todo.extend(x)
    return sorted(ids)

class Journal:
    def __init__(self,branch,head):self.branch=branch;self.head=head;self.rows=[]
    def add(self,kind,payload):
        row={'seq':len(self.rows),'branch':self.branch,'previous':self.head,'kind':kind,'policy':'E1','payload':deepcopy(payload)}
        row['digest']=digest(row);self.head=row['digest'];self.rows.append(row)

def relation(a,h,r):
    b=product(r,product(h,inverse(r)));c=product(a,product(b,product(inverse(a),inverse(b))))
    order=next(k for k in range(1,7) if all(iterate(c,x,k)==x for x in range(3)))
    fixed=[x for x in range(3) if c[x]==x]
    return {'a':a,'h':h,'r':r,'b':b,'c':c,'graph':[[0,1],[1,2],[2,0]],
            'transports':[[0,1,2],[0,1,2],c],'order':order,'fixed':fixed,
            'sections':[[x,x,x] for x in fixed],
            'capabilities':['GlobalJoin'] if fixed else ['Cyclic','Path','Reverse','Return']}

def second_joint(p,first):
    scope=digest(p)
    if p['fixed']:
        rows=[{'request':{'op':'GlobalJoin','policy':'E1','scope':scope,'section':section},
               'response':{'status':'PASS','edge_checks':[t[section[u]]==section[v] for (u,v),t in zip(p['graph'],p['transports'])]}}
              for section in p['sections']]
        rows.append({'request':{'op':'Cyclic','policy':'E1','scope':scope},
                     'response':{'status':'BLOCKED','reason':'CYCLIC_NOT_APPLICABLE'}})
    else:
        # New scoped operations are independently transported pointwise, no core executor.
        k,vertex,x=0,0,0
        def tok():return {'policy':'E1','scope':scope,'state':{'k':k,'q':k//3,'vertex':vertex,'x':x},'x0':0}
        rows=[{'request':{'op':'FormCyclic','policy':'E1','scope':scope},'response':{'status':'PASS','token':tok()}}]
        for op in ('Path','Reverse','Return','Return','Return'):
            token=deepcopy(tok());before=deepcopy(token['state']);arg=[[0,1]] if op in ('Path','Reverse') else None
            path=[[0,1]] if op=='Path' else [[1,0]] if op=='Reverse' else [[0,1],[1,2],[2,0]]
            for u,v in path:
                if u!=vertex:raise ValueError('path')
                if v==(u+1)%3:table=p['transports'][u];k=(k+1)%9
                else:table=inverse(p['transports'][v]);k=(k-1)%9
                x=table[x];vertex=v
            rows.append({'request':{'op':op,'token':token,'path':arg},'response':{'status':'PASS',
                'transition':{'path':path,'before':before,'after':deepcopy(tok()['state'])},'token':tok()}})
        rows.append({'request':{'op':'GlobalJoin','policy':'E1','scope':scope},
                     'response':{'status':'FAIL','reason':'GLOBAL_SECTION_OBSTRUCTED'}})
    rows.append({'request':{'op':'Return','policy':'E1','scope':scope,'token':deepcopy(first['joint_trace'][0]['response']['token'])},
                 'response':{'status':'FAIL','reason':'STALE_STATE_SCOPE'}})
    return rows

def second(prepared,event,first,used_ids=None):
    ctx=prepared['context'];form=prepared['formation'];m=form['definition'];actor=ctx['actor']
    j=Journal('generation2/'+prepared['first']+'/'+actor,form['certificate']['first_history_head'])
    j.add('Formation2',form);j.add('SecondContext',ctx)
    out={'semantic_version':SEM,'actor':actor,'context_ref':digest(ctx),'formation_ref':digest(form),
         'event':deepcopy(event),'status':'NOT ENACTED','reason':'WAIT','before':deepcopy(ctx['before']),
         'after':deepcopy(ctx['before']),'embedded':None,'own_steps':[],'composition':None,
         'effective_trace':None,'local_install':None,'Psi2':None,'joint_trace':[],
         'policy':'E1','covenant_ref':'C0','eta_acceptance_ref':'C0','unresolved':LIMITS}
    if event is not None:
        e=deepcopy(event);j.add('OwnEnactmentGeneration2',e)
        expected={'id','kind','actor','source','origin','covenant_ref','eta_acceptance_ref','context_ref','formation_ref',
                  'previous_psi_ref','parents','operation_scope','before','action','word'}
        valid=(set(e)==expected and type(e['id']) is str and bool(e['id']) and
               e['id'] not in ctx['reserved_event_ids'] and e['id'] not in (used_ids or set()) and
               e['id'] not in {'A0','A1','H0','h1','C0','R0','eta',form['certificate']['first_event']['id']} and
               (e['kind'],e['actor'],e['source'])==('OwnEnactmentGeneration2',actor,actor) and
               e['covenant_ref']==e['eta_acceptance_ref']=='C0' and e['context_ref']==digest(ctx) and
               e['formation_ref']==digest(form) and e['previous_psi_ref']==ctx['Psi1_ref'] and
               e['parents']==ctx['parents'] and e['operation_scope']==ctx['scope'] and e['before']==ctx['before'] and
               e['action'] in ('Own','Ordinary','Pause'))
        if not valid:out.update(status='FAIL',reason='SECOND_SOURCE_CONTEXT_OR_SCHEMA')
        elif e['origin']!='AUTHORED PREMISE':out.update(status='UNRESOLVED',reason='SECOND_ORIGIN')
        elif e['action']!='Own' and e['word']!=[]:out.update(status='FAIL',reason='WORD_NOT_APPLICABLE')
        elif e['action']=='Pause':out.update(status='PASS',reason='PAUSE')
        else:
            if ctx['before']['domain']!=[0,1,2]:raise ValueError('OUT_OF_SCOPE_REFINED_SECOND_ACTOR')
            if e['action']=='Ordinary':
                trace=ctx['before']['trace'];point=ctx['before']['value']
                rows=[{'input':i,'embedded':i,'states':[i,trace[i]],'projected':trace[i]} for i in range(3)]
                out['embedded']=point;out['after']['value']=trace[point]
                out['own_steps']=[{'step':1,'requested':'OrdinaryTrace','resolved':'OrdinaryTrace',
                                  'before':point,'after':trace[point],'table_ref':digest(trace)}]
                out.update(status='PASS',reason='ORDINARY')
            else:
                word=e['word']
                if not isinstance(word,list) or not 1<=len(word)<=3:
                    out.update(status='FAIL',reason='WORD_SCOPE');j.add('Outcome',out);out['journal']=j.rows;return out
                names=[m['aliases'].get(n,n) for n in word]
                if any(n not in m['operations'] for n in names):
                    out.update(status='FAIL',reason='OPERATOR_NOT_ADMITTED');j.add('Outcome',out);out['journal']=j.rows;return out
                lookup={encode(s):i for i,s in enumerate(m['states'])}
                funcs={n:{encode(s):t for s,t in zip(m['states'],tab)} for n,tab in m['operations'].items()}
                beta={encode(s):b for s,b in zip(m['states'],m['beta'])};rows=[]
                for i,start in enumerate(m['chi']):
                    path=[start]
                    for n in names:path.append(funcs[n][encode(path[-1])])
                    rows.append({'input':i,'embedded':start,'states':path,'projected':beta[encode(path[-1])]})
                point=ctx['before']['value'];out['embedded']=deepcopy(m['chi'][point]);actual=out['embedded']
                for k,n in enumerate(names):
                    nxt=deepcopy(funcs[n][encode(actual)])
                    out['own_steps'].append({'step':k+1,'requested':word[k],'resolved':n,'before':actual,
                                            'after':nxt,'table_ref':digest(m['operations'][n])});actual=nxt
                trace=[row['projected'] for row in rows]
                out['after']={'domain':deepcopy(m['states']),'value':actual,'beta':m['beta'],
                    'operations':deepcopy(m['operations']),'law':'local-generation2/'+digest(form),
                    'formation_trace':form['source_definition']['trace'],'effective_trace':trace}
                out['local_install']={'actor':actor,'from':ctx['before']['law'],'to':out['after']['law'],
                                      'formation_ref':digest(form),'event':e['id'],'joint_policy':'E1'}
                out.update(status='PASS',reason='ENACTED_GENERATION2_OWN_CHANGE')
            trace=[row['projected'] for row in rows]
            if not permutation(trace):raise ValueError('non S3')
            actual_beta=out['after']['value'] if e['action']=='Ordinary' else dict(zip(map(encode,m['states']),m['beta']))[encode(out['after']['value'])]
            out['composition']={'rows':rows,'effective_trace':trace,'s3_status':'PASS'};out['effective_trace']=trace
            out['point_consistency']={'actual_beta':actual_beta,'table_value':trace[ctx['before']['value']],
                                      'equal':actual_beta==trace[ctx['before']['value']]}
            for s in out['own_steps']:j.add('ActualOwnStep',s)
            j.add('EffectiveTrace2',out['composition'])
            if out['local_install']:j.add('LocalInstall2',out['local_install'])
            a=trace if actor=='A' else ctx['other_effective_trace'];h=trace if actor=='H' else ctx['other_effective_trace']
            p=relation(a,h,ctx['r']);p.update(generation=2,version='Psi2/'+e['id'],parent_psi1_ref=ctx['Psi1_ref'],enactment_ref=digest(e),policy='E1')
            out['Psi2']=p;j.add('Psi2',p);out['joint_trace']=second_joint(p,first)
            for s in out['joint_trace']:j.add('JointOperation2',s)
    j.add('Outcome',out);out['journal']=j.rows;return out

def compare(prepared,results):
    allpairs={}
    for actor,pair in (('A',('H-T','H-A')),('H',('A-S','A-R'))):
        p,q=[prepared[n] for n in pair]
        allpairs[actor]={'causality1_first_choice_to_Psi1':{'different':p['formation']['certificate']['Psi1']!=q['formation']['certificate']['Psi1']},
          'causality2_Psi1_history_to_Formation2':{'same_second_actor_local_before':p['context']['before']==q['context']['before'],
             'relative_transports':[z['formation']['certificate']['target_d'] for z in (p,q)],
             'new_word_sizes':[z['formation']['definition']['novelty']['new_size'] for z in (p,q)],
             'different_lift':p['formation']['definition']['lift_table']!=q['formation']['definition']['lift_table']},
          'causality3_second_act_to_Psi2':{n:{'event_required':True,'actual_steps':len(results[n]['own_steps']),
              'Psi2_exists':results[n]['Psi2'] is not None,'effective_trace':results[n]['effective_trace'],
              'existing_control':compare_existing(results,n),'wait_creates_Psi2':
                  results[n+'_Wait']['Psi2'] is not None if n+'_Wait' in results else None}
              for n in pair if n in results},
          'scope':'separate controlled cross-participant branches, not simultaneous persons'}
    return allpairs

def compare_existing(results,n):
    other=results.get(n+'_Existing')
    if other is None:return None
    chosen=results[n];p,q=chosen['Psi2'],other['Psi2']
    different=False
    if p is not None and q is not None:
        different=any(p[k]!=q[k] for k in ('a','h','r','c','graph','transports'))
    return {'same_prechoice_context':chosen['context_ref']==other['context_ref'],'effective_trace':other['effective_trace'],
            'different_operation_effect':chosen['effective_trace']!=other['effective_trace'],
            'different_mathematical_relation':different}

def replay(choices=None):
    g,c,f,first_choices=inputs();first=preceding.replay(g,c,f,first_choices)
    prepared={n:preparation(first,n) for n in FIRSTS};results={}
    if choices is None:choices=load(ROOT/'fixtures/second_choices.json')['cases']
    counts={}
    for c in choices.values():
        if c['event'] is not None:
            identifier=c['event']['id'];counts[identifier]=counts.get(identifier,0)+1
    seen={i for i,n in counts.items() if n>1}
    for name,case in choices.items():
        n=case['first'];e=case['event'];b=second(prepared[n],e,first['branches'][n],seen)
        if e:seen.add(e['id'])
        results[name]=b
    return {'schema':'source-x-two-generation/0.4','generation1':first,'prepared':prepared,'branches':results,
        'comparisons':compare(prepared,results),'formal_novelty_against_E0plus':'FAIL','unresolved':LIMITS,
        'scope':'clean cross-participant ONLY; already-refined continuation OUT OF SCOPE / BLOCKED','Seal_limit':first['Seal_limit']}

@lru_cache(maxsize=16)
def expected(encoded_choices):return replay(json.loads(encoded_choices))

def verify(artifact,choices=None):
    if choices is None:choices=load(ROOT/'fixtures/second_choices.json')['cases']
    try:
        from location4 import protected_integrity
        protected_integrity()
        problems=old_diff.differences(artifact,expected(encode(choices).decode()))
    except (ValueError,TypeError,KeyError,IndexError) as e:problems=['malformed: '+str(e)]
    return {'status':'FAIL' if problems else 'PASS','problems':problems[:80],
            'scope':'independent two-generation replay, conditional authored sources','unresolved':LIMITS}

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--artifact',required=True);a=p.parse_args()
    result=verify(load(a.artifact));print(encode(result).decode(),end='')
    raise SystemExit(0 if result['status']=='PASS' else 1)
