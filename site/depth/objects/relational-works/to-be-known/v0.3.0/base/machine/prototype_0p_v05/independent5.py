"""Independent new mathematics and historical reconstruction. No core/algebra imports."""
from copy import deepcopy
from functools import lru_cache
from collections import Counter
from support5 import ROOT,OLD,load,encode,digest,integrity,plans
import checker4 as preceding

SEM='already-refined/0.5'
PROFILE={'ordinary':'R','word_policy':'W1','REL_bound':[1,3],'mixed':False,'install':'Own PROPOSAL after independent admission',
         'ordinary_REL_install':False,'partial_local_actual':'OUT OF SCOPE','joint_policy':'E1'}
LIMITS={'Strong CO-EVOLVE':'UNRESOLVED','X4':'UNRESOLVED','H-2':'UNRESOLVED','r-origin':'UNRESOLVED',
        'external subjectivity/consciousness/free will':'UNRESOLVED','personal/numerical identity':'UNRESOLVED','C7':'UNRESOLVED'}

def product(f,g):return [f[g[i]] for i in range(len(g))]
def perm(p):return type(p) is list and len(p)==3 and all(type(i) is int for i in p) and set(p)=={0,1,2}
def invert(p):
    if not perm(p):raise ValueError('INTERFACE_NOT_BIJECTIVE')
    d={j:i for i,j in enumerate(p)};return [d[i] for i in range(3)]
def word_maps(ops):
    # Right multiplication and shortlex relaxation, independently of core BFS.
    n=len(next(iter(ops.values())));known={tuple(range(n)):[]}
    while True:
        change=False
        for f,w in list(sorted(known.items())):
            for name in sorted(ops):
                g=ops[name];out=tuple(f[g[i]] for i in range(n));word=[name]+w
                if out not in known or (len(word),word)<(len(known[out]),known[out]):known[out]=word;change=True
        if not change:return known
def reach(ops,point):
    known={point}
    while True:
        after=known|{p[i] for p in ops.values() for i in known}
        if after==known:return sorted(known)
        known=after
def structural(o):
    st=o['states'];positions={tuple(s):i for i,s in enumerate(st)};emb={i:positions[tuple(s)] for i,s in enumerate(o['chi'])}
    projection={i:b for i,b in enumerate(o['beta'])};trace=[projection[emb[i]] for i in range(3)]
    if not perm(trace):raise ValueError('STRUCTURAL_CHI')
    e={i:emb[next(j for j in range(3) if trace[j]==i)] for i in range(3)}
    rows=[]
    if o['actor']=='H':
        T=dict(enumerate(o['rel'][o['names']['Turn']]))
        for i in range(3):
            r=[e[i],T[e[i]],T[T[e[i]]]]
            if len(set(r))!=3 or T[r[-1]]!=r[0] or any(projection[j]!=i for j in r):raise ValueError('H_NORMAL_FORMS')
            rows.append(r)
    else:
        seal=dict(enumerate(o['rel'][o['names']['Seal']]))
        for i in range(3):
            r=[seal[e[i]],e[i]]
            if r[0]==r[1] or seal[r[0]]!=r[0] or any(projection[j]!=i for j in r):raise ValueError('A_MARKED_LAYERS')
            rows.append(r)
    if sorted(j for r in rows for j in r)!=list(range(len(st))):raise ValueError('STRUCTURAL_COVERAGE')
    return rows
def Q(o):
    d=o['ordinary_delta'];rows=structural(o);result={}
    if not perm(d):raise ValueError('ORDINARY_DELTA')
    for i in range(3):
        for z,j in enumerate(rows[i]):result[j]=rows[d[i]][z]
    table=[result[i] for i in range(len(o['states']))]
    if len(set(table))!=len(table) or any(table[table[i]]!=i for i in range(len(table))):raise ValueError('Q_NOT_INVOLUTION')
    if any(o['beta'][table[i]]!=d[o['beta'][i]] for i in range(len(table))):raise ValueError('Q_BETA')
    return table
def lifted(o,d):
    if not perm(d):raise ValueError('D_TYPE')
    rows=structural(o);pairs={}
    for i,row in enumerate(rows):
        if o['actor']=='H':pairs.update({row[0]:row[1],row[1]:row[2],row[2]:rows[d[i]][0]})
        else:pairs.update({row[0]:row[0],row[1]:rows[d[i]][0]})
    return [pairs[i] for i in range(len(o['states']))]
def execute(o,word,ops=None):
    ops=o['rel'] if ops is None else ops;st=o['states']
    funcs={n:{tuple(s):deepcopy(st[j]) for s,j in zip(st,t)} for n,t in ops.items()}
    pathrows=[]
    for i,start in enumerate(o['sigma']):
        path=[deepcopy(start)]
        for name in word:path.append(deepcopy(funcs[name][tuple(path[-1])]))
        pathrows.append({'input':i,'states':path,'projected':o['beta'][st.index(path[-1])]})
    at=deepcopy(o['point']);steps=[]
    for k,n in enumerate(word):
        nxt=deepcopy(funcs[n][tuple(at)]);steps.append({'step':k+1,'operator':n,'before':at,'after':nxt,'table_ref':digest(ops[n])});at=nxt
    sigma=[r['states'][-1] for r in pathrows]
    if at!=sigma[o['input']]:raise ValueError('ACTUAL_POINT_CONSISTENCY')
    return {'steps':steps,'sigma':sigma,'point':at,'rows':pathrows,'cumulative':[r['projected'] for r in pathrows]}
def replay_frame(o):
    st=o['states'];f={n:{tuple(s):st[j] for s,j in zip(st,t)} for n,t in o['rel'].items()}
    f[o['ordinary_key']]={tuple(s):st[j] for s,j in zip(st,Q(o))};sigma=deepcopy(o['chi'])
    for e in o['path']:
        for n in e['word']:sigma=[deepcopy(f[n][tuple(s)]) for s in sigma]
    if sigma!=o['sigma'] or sigma[o['input']]!=o['point']:raise ValueError('OWN_HISTORY_SIGMA')
    if len(o['J'])!=3 or len(o['I'])!=3 or not perm(o['kappa']):raise ValueError('COORDINATE_DOMAIN')
    if o['marks']!=[[deepcopy(st[j]) for j in r] for r in structural(o)]:raise ValueError('FIXED_MARKS')
    return sigma
def edge_product(p,path):
    out=[0,1,2]
    for a,b in path:
        if [a,b] in p['graph']:f=p['transports'][p['graph'].index([a,b])]
        elif [b,a] in p['graph']:f=invert(p['transports'][p['graph'].index([b,a])])
        else:raise ValueError('HISTORICAL_PATH_DOMAIN')
        out=[f[out[i]] for i in range(3)]
    return out
def evidence(w,B):
    z=w['witness'];W=z['W'];p=z['proposal'];old=z['old'];new=z['target'];squares=[]
    if W['status']!='PASS' or W['scope']!='historical orbit, NOT current monodromy':raise ValueError('W_SCOPE')
    if p['source_event_ref']!=z['event']['id']:raise ValueError('W_SOURCE')
    for edge,transport in zip(old['graph'],old['transports']):
        a,b=edge;target=edge_product(new,p['paths'][str(a)+'-'+str(b)])
        left=[p['phi'][b][transport[i]] for i in range(3)];right=[target[p['phi'][a][i]] for i in range(3)]
        if left!=right:raise ValueError('W_K_PHI')
        squares.append({'edge':edge,'left':left,'right':right})
    loop=edge_product(old,W['path']);phi=p['phi'][0];f=[phi[0],phi[loop[0]],phi[loop[loop[0]]]]
    if sorted(f)!=[0,1,2]:raise ValueError('W_ORBIT')
    tau=[f[(f.index(i)+1)%3] for i in range(3)];ell=z['ell'];r=w['Psi']['r']
    if ell!=W['address_map'] or not perm(ell) or not perm(r):raise ValueError('W_ADDRESS')
    if tau!=W['successor']:raise ValueError('W_SUCCESSOR')
    if w['Psi']['graph']!=[[0,1],[1,2],[2,0]]:raise ValueError('CURRENT_CYCLE_DOMAIN')
    t=product(ell,product(tau,invert(ell)));D=[invert(t)[w['Psi']['c'][i]] for i in range(3)]
    d=D if B=='A' else product(invert(r),product(D,r))
    return {'W_ref':digest(W),'W_scope':W['scope'],'squares':squares,'tau_hist':tau,'ell':ell,'tau_hat':t,'r':r,
            'current_Psi_ref':digest(w['Psi']),'history_head':w['history_head'],'D':D,'target_d':d,'actor':B,
            'source_tier':'AUTHORED PREMISE / STRUCTURALLY VERIFIED'}
def psi(a,h,r):
    if not all(perm(p) for p in (a,h,r)):raise ValueError('JOINT_S3')
    b=[r[h[invert(r)[i]]] for i in range(3)]
    c=[a[b[invert(a)[invert(b)[i]]]] for i in range(3)]
    q=[0,1,2];order=None
    for k in range(1,7):
        q=[c[q[i]] for i in range(3)]
        if q==[0,1,2]:order=k;break
    fix=[i for i in range(3) if c[i]==i]
    return {'a':a,'h':h,'r':r,'b':b,'c':c,'graph':[[0,1],[1,2],[2,0]],'transports':[[0,1,2],[0,1,2],c],
            'order':order,'fixed':fix,'sections':[[i,i,i] for i in fix],
            'capabilities':['GlobalJoin'] if fix else ['Cyclic','Path','Reverse','Return']}
def joint_receipts(p,old):
    scope=digest(p);rows=[]
    if p['fixed']:
        for section in p['sections']:
            checks=[table[section[u]]==section[v] for (u,v),table in zip(p['graph'],p['transports'])]
            rows.append({'op':'GlobalJoin','scope':scope,'section':section,'status':'PASS' if all(checks) else 'FAIL','checks':checks})
        rows.append({'op':'Cyclic','scope':scope,'status':'BLOCKED','reason':'CYCLIC_NOT_APPLICABLE'})
    else:
        if p['order']!=3:raise ValueError('E1_CYCLIC_PROFILE')
        state={'vertex':0,'x':0,'k':0,'q':0};rows.append({'op':'FormCyclic','scope':scope,'status':'PASS','state':deepcopy(state)})
        for name,path in [('Path',[[0,1]]),('Reverse',[[1,0]]),('Return',p['graph']),('Return',p['graph']),('Return',p['graph'])]:
            before=deepcopy(state)
            for u,v in path:
                if state['vertex']!=u:raise ValueError('JOINT_PATH_START')
                forward=[u,v] in p['graph'];index=p['graph'].index([u,v] if forward else [v,u]);table=p['transports'][index]
                if not forward:table=invert(table)
                k=(state['k']+(1 if forward else -1))%9
                state={'vertex':v,'x':table[state['x']],'k':k,'q':k//3}
            rows.append({'op':name,'scope':scope,'status':'PASS','before':before,'after':deepcopy(state),'path':deepcopy(path)})
        rows.append({'op':'GlobalJoin','scope':scope,'status':'FAIL','reason':'GLOBAL_SECTION_OBSTRUCTED'})
    rows.append({'op':'ReturnOldToken','scope':scope,'old_scope':digest(old),'status':'FAIL','reason':'STALE_STATE_SCOPE'})
    return rows
def formation(w,B):
    o=w['actors'][B];replay_frame(o);cert=evidence(w,B);candidate=lifted(o,cert['target_d']);ordinary=Q(o)
    rel=word_maps(o['rel']);allops=dict(o['rel']);allops[o['ordinary_key']]=ordinary;ALL=word_maps(allops)
    rp=dict(o['rel']);rp['candidate']=candidate;ap=dict(allops);ap['candidate']=candidate
    point=o['states'].index(o['point']);R=reach(o['rel'],point);RA=reach(allops,point)
    member=tuple(candidate) in rel;memberALL=tuple(candidate) in ALL
    definition={'actor':B,'kind':'L_d' if B=='H' else 'M_d','initial_ref':o['initial_ref'],'certificate_ref':digest(cert),'table':candidate}
    key=B+'::'+digest(definition)+'::'+definition['kind'];new=not member and not memberALL
    extension=deepcopy(o['rel']);defs=deepcopy(o['definitions'])
    if new:extension[key]=candidate;defs[key]={'name':definition['kind'],'definition_ref':digest(definition),'installed_by':None}
    relrestrict={tuple(f[i] for i in R) for f in rel};allrestrict={tuple(f[i] for i in RA) for f in ALL}
    metrics={'REL_size':len(rel),'ALL_size':len(ALL),'REL_plus_size':len(word_maps(rp)),'ALL_plus_size':len(word_maps(ap)),
             'REL_member':member,'ALL_member':memberALL,'REL_word':rel.get(tuple(candidate)),'ALL_word':ALL.get(tuple(candidate)),
             'REL_maps':sorted(map(list,rel)),'ALL_maps':sorted(map(list,ALL)),
             'reachable_REL':[o['states'][i] for i in R],'reachable_ALL':[o['states'][i] for i in RA],
             'reachable_plus':[o['states'][i] for i in reach(ap,point)],
             'new_reachable_map_REL':tuple(candidate[i] for i in R) not in relrestrict,
             'new_reachable_map_ALL':tuple(candidate[i] for i in RA) not in allrestrict,
             'new_endpoint':candidate[point] not in RA,'atomic_selector_added':new,
             'verdict':'NEW FULL MAP' if new else 'DEFINABLE / NOT A NEW ATOM',
             'admissible_current_REL':member and 1<=len(rel[tuple(candidate)])<=3}
    return {'actor':B,'certificate':cert,'definition':definition,'candidate_key':key,'metrics':metrics,
            'rel_extension':extension,'definitions':defs,'proposal_only':True,'enacted':False,
            'identity_inclusion':list(range(len(o['states']))),'preserved_point':deepcopy(o['point']),
            'old_signature_ref':digest(o['rel']),'structural_ref':o['initial_ref']}
@lru_cache(maxsize=1)
def old_replay():
    integrity();a=preceding.replay()
    if a!=load(OLD[0]/'evidence/final1/core_evidence.json'):raise ValueError('OLD_INDEPENDENT_REPLAY')
    return a
def old_ids(a):
    stack=[a];found=set()
    while stack:
        o=stack.pop()
        if type(o) is dict:
            if 'kind' in o and type(o.get('id')) is str:found.add(o['id'])
            stack.extend(o.values())
        elif type(o) is list:stack.extend(o)
    return found
def seed(a,name):
    if name not in ('H-T','H-A','A-S','A-R'):raise ValueError('SEED_SCOPE')
    first=a['generation1']['branches'][name];second=a['branches'][name];latest={first['event']['actor']:first,second['actor']:second};actors={}
    for B in ('A','H'):
        n=latest[B];f=a['generation1']['contexts'][B]['formation'];ref=digest(f);st=deepcopy(f['states']);pos={tuple(s):i for i,s in enumerate(st)}
        names={};rel={};defs={}
        for label,tab in n['after']['operations'].items():
            origin=ref if label in f['operations'] else second['formation_ref'];key=B+'::'+origin+'::'+label
            names[label]=key;rel[key]=[pos[tuple(s)] for s in tab];defs[key]={'name':label,'definition_ref':origin,'installed_by':n['event']['id']}
        word=([names[n['event']['selected_operation']]] if n is first else [names[s['resolved']] for s in n['own_steps']])
        o={'actor':B,'states':st,'I':[0,1,2],'J':[0,1,2],'input':1,'kappa':[0,1,2],
           'interface_scope':B+'/I','input_scope':B+'/J/'+ref,'beta':deepcopy(f['beta']),'chi':deepcopy(f['embedding']),
           'initial_ref':ref,'names':names,'rel':rel,'definitions':defs,'marks':[],
           'point':deepcopy(f['embedding'][1]),'sigma':deepcopy(f['embedding']),'path':[],
           'ordinary_key':B+'::Ordinary_R_Q_delta/0.5','ordinary_delta':[1,0,2],
           'law_version':n['after']['law'],'state_version':digest(n['after']),'source_event_ref':digest(n['event'])}
        o['marks']=[[deepcopy(st[i]) for i in r] for r in structural(o)];actual=execute(o,word)
        saved=[r['operated'] if n is first else r['states'][-1] for r in n['composition']['rows']]
        if saved!=actual['sigma'] or n['after']['value']!=actual['point'] or n['effective_trace']!=actual['cumulative']:raise ValueError('SEED_OWN_REPLAY')
        o['sigma']=actual['sigma'];o['point']=actual['point'];o['path']=[{'id':n['event']['id'],'source':B,'event_ref':digest(n['event']),
            'word':word,'steps':actual['steps'],'origin':'ACTUAL PRIOR AUTHORED EVENT'}]
        replay_frame(o);actors[B]=o
    hist=a['generation1']['prefix']['histories']['alpha'];p=hist['prefix']
    return {'seed':name,'actors':actors,'Psi':deepcopy(second['Psi2']),
            'witness':{'W':deepcopy(a['generation1']['contexts']['H']['W']),'old':deepcopy(p['psi1']),
                       'target':deepcopy(p['psi2']),'proposal':deepcopy(p['proposal']),'event':deepcopy(p['candidate']),'ell':deepcopy(hist['address_map'])},
            'history_head':second['journal'][-1]['digest'],'accepted_ids':[],'historical_ref':digest(a),
            'policy':'E1','covenant_ref':'C0','eta_acceptance_ref':'C0','profile':deepcopy(PROFILE)}
def prepare(w,B,slot):
    P=formation(w,B)
    return {'context':{'slot':slot,'actor':B,'world_ref':digest(w),'own_ref':digest(w['actors'][B]),
             'own_version':w['actors'][B]['state_version'],'Psi_parent':digest(w['Psi']),'history_parent':w['history_head'],
             'formation_ref':digest(P),'input_scope':w['actors'][B]['input_scope'],'policy':'E1','profile':deepcopy(PROFILE)},'formation':P}
def transition(w,prepared,e,forbidden):
    out={'status':'WAIT','accepted':False,'reason':'NO_EVENT','event':deepcopy(e),'own_steps':[],
         'sigma_before':None,'sigma_next':None,'cumulative':None,'relative':None,'rows':[],
         'next_actor':None,'next_Psi':None,'joint_trace':[],'installation':None}
    if e is None:return out
    C=prepared['context'];P=prepared['formation'];B=C['actor'];o=w['actors'][B]
    def no(reason):out.update(status='REJECTED',reason=reason,installation=None,next_actor=None,next_Psi=None);return out
    fields={'id','kind','actor','source','origin','covenant_ref','eta_acceptance_ref','context_ref','formation_ref',
            'before_ref','before_version','Psi_parent','history_parent','input_scope','action','mode','word'}
    if set(e)!=fields or e['kind']!='OwnContinuation05':return no('EVENT_SCHEMA')
    if type(e['id']) is not str or not e['id'] or e['id'] in forbidden or e['id'] in w['accepted_ids'] or e['id'] in {'C0','eta'}:return no('EVENT_ID')
    if (e['actor'],e['source'])!=(B,B):return no('ACTOR_SOURCE')
    if e['origin']!='AUTHORED PREMISE':return no('UNRESOLVED_ORIGIN')
    if e['covenant_ref']!='C0' or e['eta_acceptance_ref']!='C0':return no('COVENANT')
    if e['before_ref']!=digest(o) or e['before_version']!=o['state_version']:return no('STALE_OWN_BEFORE')
    if e['Psi_parent']!=digest(w['Psi']):return no('STALE_PSI_PARENT')
    if (e['history_parent']!=w['history_head'] or e['context_ref']!=digest(C) or e['formation_ref']!=digest(P) or e['input_scope']!=o['input_scope']):return no('STALE_CONTEXT_OR_FORMATION')
    if e['action'] not in ('Own','Ordinary','Pause') or e['mode'] not in ('CURRENT','PROPOSAL') or type(e['word']) is not list:return no('ACTION_SCHEMA')
    if e['action'] in ('Ordinary','Pause') and (e['mode']!='CURRENT' or e['word']):return no('NON_OWN_WORD_OR_INSTALL')
    if e['action']=='Pause':out.update(status='PAUSE',accepted=True,reason='LAWFUL_PAUSE');return out
    try:
        replay_frame(o);actor=deepcopy(o)
        if e['action']=='Ordinary':word=[o['ordinary_key']];ops={word[0]:Q(o)}
        else:
            word=e['word']
            if not 1<=len(word)<=3:return no('WORD_LENGTH')
            if any(k==o['ordinary_key'] or 'Ordinary' in str(k) for k in word):return no('MIXED_FAMILY')
            ops=o['rel'] if e['mode']=='CURRENT' else P['rel_extension']
            if any(k not in ops for k in word):return no('OPERATOR_OR_ALIAS_NOT_ADMITTED')
            if e['mode']=='PROPOSAL':
                actor['rel']=deepcopy(P['rel_extension']);actor['definitions']=deepcopy(P['definitions'])
                for k in set(actor['rel'])-set(o['rel']):actor['definitions'][k]['installed_by']=e['id']
                actor['law_version']='local/0.5/'+digest(P)
                out['installation']={'from':o['law_version'],'to':actor['law_version'],'event':e['id'],
                                     'added':sorted(set(actor['rel'])-set(o['rel'])),'formation_ref':digest(P)}
        run=execute(o,word,ops)
        if not perm(run['cumulative']):return no('CUMULATIVE_NOT_S3')
        actor['point']=run['point'];actor['sigma']=run['sigma'];actor['source_event_ref']=digest(e)
        actor['path'].append({'id':e['id'],'source':B,'event_ref':digest(e),'word':word,'steps':run['steps'],
                              'origin':'ACCEPTED OWN EVENT' if e['action']=='Own' else 'ACCEPTED ORDINARY EVENT'})
        actor['state_version']=digest({'before':digest(o),'event':digest(e),'point':actor['point'],'sigma':actor['sigma'],'law':actor['law_version']})
        q=product(run['cumulative'],invert(o['kappa']));other=w['actors']['H' if B=='A' else 'A']
        otherq=product([other['beta'][other['states'].index(s)] for s in other['sigma']],invert(other['kappa']))
        p=psi(q if B=='A' else otherq,q if B=='H' else otherq,w['Psi']['r'])
        p.update(version='Psi/0.5/'+e['id'],parent_ref=digest(w['Psi']),event_ref=digest(e),policy='E1')
        oldtrace=[o['beta'][o['states'].index(s)] for s in o['sigma']]
        out.update(status='ACCEPTED',accepted=True,reason='OWN_ENACTED' if e['action']=='Own' else 'ORDINARY_ENACTED',
                   own_steps=run['steps'],sigma_before=deepcopy(o['sigma']),sigma_next=run['sigma'],cumulative=run['cumulative'],
                   relative=product(run['cumulative'],invert(oldtrace)),rows=run['rows'],next_actor=actor,next_Psi=p,
                   joint_trace=joint_receipts(p,w['Psi']))
    except (ValueError,KeyError,TypeError,IndexError) as exc:return no(str(exc))
    return out
def differences(a,b,path='$'):
    if type(a)!=type(b):return [path+':type']
    if isinstance(a,dict):
        rows=[path+'.keys'] if set(a)!=set(b) else []
        for k in sorted(set(a)&set(b)):rows.extend(differences(a[k],b[k],path+'.'+k))
        return rows
    if isinstance(a,list):
        rows=[path+'.length'] if len(a)!=len(b) else []
        for i,(v,w) in enumerate(zip(a,b)):rows.extend(differences(v,w,path+'['+str(i)+']'))
        return rows
    return [] if a==b else [path]
def check_admission(w,p,e,forbidden,preview):
    try:
        independent_p=prepare(w,p['context']['actor'],p['context']['slot'])
        expected=transition(w,independent_p,e,forbidden)
        bad=differences(p,independent_p,'$.prepared')+differences(preview,expected,'$.preview')
    except (ValueError,KeyError,TypeError,IndexError) as exc:bad=['malformed:'+str(exc)]
    return {'status':'FAIL' if bad else 'PASS','differences':bad[:60],'scope':'independent pre-acceptance finite reconstruction'}
def accepted(w,preview):
    out=deepcopy(w)
    if not preview['accepted']:return out,None
    e=preview['event'];row={'seq':len(w['accepted_ids']),'previous':w['history_head'],
                          'kind':'Pause' if preview['status']=='PAUSE' else 'AcceptedContinuation','payload':deepcopy(preview)}
    row['digest']=digest(row);out['history_head']=row['digest'];out['accepted_ids'].append(e['id'])
    if preview['next_actor'] is not None:out['actors'][e['actor']]=deepcopy(preview['next_actor']);out['Psi']=deepcopy(preview['next_Psi'])
    return out,row
def replay(choices=None):
    integrity();a=old_replay();layout=plans()
    if choices is None:choices=load(ROOT/'fixtures/choices.json')['cases']
    events=[e for es in choices.values() for e in es if e is not None];counts=Counter(e.get('id') for e in events if type(e.get('id')) is str)
    forbidden=old_ids(a)|{i for i,n in counts.items() if n>1};trials={}
    for name,c in sorted(layout.items()):
        initial=seed(a,c['seed']);w=deepcopy(initial);stages=[];ledger=[]
        for i,B in enumerate(c['actors']):
            if i and not stages[-1]['preview']['accepted']:
                stages.append({'slot':name+'/'+str(i),'blocked':'DEPENDENCY_NOT_ACCEPTED','event':None});break
            p=prepare(w,B,name+'/'+str(i));es=choices.get(name,[]);e=deepcopy(es[i]) if i<len(es) else None
            outcome=transition(w,p,e,forbidden)
            checked=check_admission(w,p,e,forbidden,outcome);after,row=accepted(w,outcome)
            stages.append({'slot':name+'/'+str(i),'before':deepcopy(w),'prepared':p,'event':e,'preview':outcome,
                           'independent_admission':checked,'after':deepcopy(after),'ledger_entry':row})
            if row:ledger.append(row)
            w=after
        trials[name]={'seed':c['seed'],'initial':initial,'stages':stages,'accepted_ledger':ledger,'final':w}
    return {'schema':SEM,'profile':deepcopy(PROFILE),'historical':a,'trials':trials,
            'formal_novelty_against_E0plus':'FAIL','limits':deepcopy(LIMITS),
            'scope':'finite authored already-refined continuation; no external identity claim'}
@lru_cache(maxsize=8)
def expected(choices_bytes):return replay(__import__('json').loads(choices_bytes))
def verify(artifact,choices=None):
    if choices is None:choices=load(ROOT/'fixtures/choices.json')['cases']
    try:integrity();bad=differences(artifact,expected(encode(choices).decode()))
    except (ValueError,KeyError,TypeError,IndexError) as exc:bad=['malformed:'+str(exc)]
    return {'status':'FAIL' if bad else 'PASS','differences':bad[:160],'scope':'independent full already-refined replay','limits':deepcopy(LIMITS)}

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--artifact',required=True);args=p.parse_args()
    result=verify(load(args.artifact));print(encode(result).decode(),end='')
    raise SystemExit(0 if result['status']=='PASS' else 1)
