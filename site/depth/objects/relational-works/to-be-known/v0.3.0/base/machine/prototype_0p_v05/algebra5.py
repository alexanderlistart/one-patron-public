"""Core-only finite mathematics. No choice generation or file output."""
from copy import deepcopy
from collections import deque
from support5 import digest

I=[0,1,2]
def mul(f,g):return [f[j] for j in g]
def inverse(p):
    if not permutation(p):raise ValueError('INTERFACE_NOT_BIJECTIVE')
    return [p.index(i) for i in I]
def permutation(p):return type(p) is list and len(p)==3 and all(type(i) is int for i in p) and sorted(p)==I
def closure(ops):
    n=len(next(iter(ops.values())));e=tuple(range(n));seen={e:[]};todo=deque([e])
    while todo:
        a=todo.popleft()
        for name in sorted(ops):
            b=tuple(ops[name][j] for j in a)
            if b not in seen:seen[b]=seen[a]+[name];todo.append(b)
    return seen
def reachable(ops,point):
    seen={point};todo=[point]
    while todo:
        a=todo.pop()
        for f in ops.values():
            if f[a] not in seen:seen.add(f[a]);todo.append(f[a])
    return sorted(seen)
def normals(o):
    st=o['states'];beta=o['beta'];chi=[st.index(s) for s in o['chi']]
    t=[beta[j] for j in chi]
    if not permutation(t):raise ValueError('STRUCTURAL_CHI')
    e=[chi[t.index(i)] for i in I]
    if o['actor']=='H':
        T=o['rel'][o['names']['Turn']];rows=[[e[i],T[e[i]],T[T[e[i]]]] for i in I]
        if any(len(set(r))!=3 or T[r[-1]]!=r[0] or any(beta[x]!=i for x in r) for i,r in enumerate(rows)):
            raise ValueError('H_NORMAL_FORMS')
    else:
        S=o['rel'][o['names']['Seal']];rows=[[S[e[i]],e[i]] for i in I]
        if any(r[0]==r[1] or S[r[0]]!=r[0] or any(beta[x]!=i for x in r) for i,r in enumerate(rows)):
            raise ValueError('A_MARKED_LAYERS')
    if sorted(x for r in rows for x in r)!=list(range(len(st))):raise ValueError('STRUCTURAL_COVERAGE')
    return rows
def ordinary(o):
    rows=normals(o);d=o['ordinary_delta'];out=[None]*len(o['states'])
    if not permutation(d):raise ValueError('ORDINARY_DELTA')
    for i,r in enumerate(rows):
        for z,j in enumerate(r):out[j]=rows[d[i]][z]
    if sorted(out)!=list(range(len(out))) or mul(out,out)!=list(range(len(out))):raise ValueError('Q_NOT_INVOLUTION')
    if [o['beta'][j] for j in out]!=[d[b] for b in o['beta']]:raise ValueError('Q_BETA')
    return out
def lift(o,d):
    if not permutation(d):raise ValueError('D_TYPE')
    rows=normals(o);out=[None]*len(o['states'])
    for i,r in enumerate(rows):
        if o['actor']=='H':out[r[0]],out[r[1]],out[r[2]]=r[1],r[2],rows[d[i]][0]
        else:out[r[0]],out[r[1]]=r[0],rows[d[i]][0]
    return out
def apply(o,word,sigma=None,point=None,ops=None):
    ops=o['rel'] if ops is None else ops;st=o['states']
    starts=o['sigma'] if sigma is None else sigma;at=o['point'] if point is None else point
    paths=[[deepcopy(s)] for s in starts];steps=[]
    for k,name in enumerate(word):
        table=ops[name];after=deepcopy(st[table[st.index(at)]])
        steps.append({'step':k+1,'operator':name,'before':deepcopy(at),'after':after,'table_ref':digest(table)})
        at=after
        for path in paths:path.append(deepcopy(st[table[st.index(path[-1])]]))
    sigma_next=[p[-1] for p in paths];cum=[o['beta'][st.index(s)] for s in sigma_next]
    if at!=sigma_next[o['input']]:raise ValueError('ACTUAL_POINT_CONSISTENCY')
    return {'steps':steps,'sigma':sigma_next,'point':at,'rows':[{'input':i,'states':p,'projected':cum[i]} for i,p in enumerate(paths)],'cumulative':cum}
def frame_replay(o):
    st=o['states'];sigma=deepcopy(o['chi'])
    for event in o['path']:
        for name in event['word']:
            table=ordinary(o) if name==o['ordinary_key'] else o['rel'][name]
            sigma=[deepcopy(st[table[st.index(s)]]) for s in sigma]
    if sigma!=o['sigma'] or sigma[o['input']]!=o['point']:raise ValueError('OWN_HISTORY_SIGMA')
    if len(o['J'])!=3 or len(o['I'])!=3 or not permutation(o['kappa']):raise ValueError('COORDINATE_DOMAIN')
    if o['marks']!=[[deepcopy(st[j]) for j in r] for r in normals(o)]:raise ValueError('FIXED_MARKS')
    return sigma
def along(p,path):
    out=I[:]
    for edge in path:
        if edge in p['graph']:f=p['transports'][p['graph'].index(edge)]
        elif list(reversed(edge)) in p['graph']:f=inverse(p['transports'][p['graph'].index(list(reversed(edge)))])
        else:raise ValueError('HISTORICAL_PATH_DOMAIN')
        out=mul(f,out)
    return out
def certificate(w,B):
    z=w['witness'];p=z['proposal'];old=z['old'];target=z['target'];W=z['W'];squares=[]
    if W['status']!='PASS' or W['scope']!='historical orbit, NOT current monodromy':raise ValueError('W_SCOPE')
    if p['source_event_ref']!=z['event']['id']:raise ValueError('W_SOURCE')
    for edge,t in zip(old['graph'],old['transports']):
        a,b=edge;path=p['paths'][str(a)+'-'+str(b)]
        left=mul(p['phi'][b],t);right=mul(along(target,path),p['phi'][a])
        if left!=right:raise ValueError('W_K_PHI')
        squares.append({'edge':edge,'left':left,'right':right})
    loop=along(old,W['path']);f=p['phi'][0];frame=[f[0],f[loop[0]],f[loop[loop[0]]]]
    if sorted(frame)!=I:raise ValueError('W_ORBIT')
    tau=[frame[(frame.index(i)+1)%3] for i in I]
    ell=z['ell'];r=w['Psi']['r']
    if ell!=W['address_map'] or not permutation(ell) or not permutation(r):raise ValueError('W_ADDRESS')
    if tau!=W['successor']:raise ValueError('W_SUCCESSOR')
    if w['Psi']['graph']!=[[0,1],[1,2],[2,0]]:raise ValueError('CURRENT_CYCLE_DOMAIN')
    that=mul(ell,mul(tau,inverse(ell)));D=mul(inverse(that),w['Psi']['c']);d=D if B=='A' else mul(inverse(r),mul(D,r))
    return {'W_ref':digest(W),'W_scope':W['scope'],'squares':squares,'tau_hist':tau,'ell':ell,'tau_hat':that,'r':r,
            'current_Psi_ref':digest(w['Psi']),'history_head':w['history_head'],'D':D,'target_d':d,'actor':B,
            'source_tier':'AUTHORED PREMISE / STRUCTURALLY VERIFIED'}
def relation(a,h,r):
    if not all(permutation(p) for p in (a,h,r)):raise ValueError('JOINT_S3')
    b=mul(r,mul(h,inverse(r)));c=mul(a,mul(b,mul(inverse(a),inverse(b))))
    fixed=[i for i in I if c[i]==i];power=I[:];order=None
    for k in range(1,7):
        power=mul(c,power)
        if power==I:order=k;break
    return {'a':a,'h':h,'r':r,'b':b,'c':c,'graph':[[0,1],[1,2],[2,0]],'transports':[I[:],I[:],c],
            'order':order,'fixed':fixed,'sections':[[i,i,i] for i in fixed],
            'capabilities':['GlobalJoin'] if fixed else ['Cyclic','Path','Reverse','Return']}
def joint(p,old):
    scope=digest(p);out=[]
    if p['fixed']:
        for section in p['sections']:
            checks=[t[section[a]]==section[b] for (a,b),t in zip(p['graph'],p['transports'])]
            out.append({'op':'GlobalJoin','scope':scope,'section':section,'status':'PASS' if all(checks) else 'FAIL','checks':checks})
        out.append({'op':'Cyclic','scope':scope,'status':'BLOCKED','reason':'CYCLIC_NOT_APPLICABLE'})
    else:
        if p['order']!=3:raise ValueError('E1_CYCLIC_PROFILE')
        vertex=0;x=0;k=0
        def state():return {'vertex':vertex,'x':x,'k':k,'q':k//3}
        out.append({'op':'FormCyclic','scope':scope,'status':'PASS','state':state()})
        for name,path in [('Path',[[0,1]]),('Reverse',[[1,0]]),('Return',p['graph']),('Return',p['graph']),('Return',p['graph'])]:
            before=state()
            for a,b in path:
                if a!=vertex:raise ValueError('JOINT_PATH_START')
                forward=[a,b] in p['graph'];table=p['transports'][p['graph'].index([a,b] if forward else [b,a])]
                x=(table if forward else inverse(table))[x];vertex=b;k=(k+(1 if forward else -1))%9
            out.append({'op':name,'scope':scope,'status':'PASS','before':before,'after':state(),'path':deepcopy(path)})
        out.append({'op':'GlobalJoin','scope':scope,'status':'FAIL','reason':'GLOBAL_SECTION_OBSTRUCTED'})
    out.append({'op':'ReturnOldToken','scope':scope,'old_scope':digest(old),'status':'FAIL','reason':'STALE_STATE_SCOPE'})
    return out
def proposal(w,B):
    o=w['actors'][B];frame_replay(o);cert=certificate(w,B);p=lift(o,cert['target_d']);Q=ordinary(o)
    rel=closure(o['rel']);allops=dict(o['rel']);allops[o['ordinary_key']]=Q;ALL=closure(allops)
    cp=dict(o['rel']);cp['candidate']=p;ap=dict(allops);ap['candidate']=p
    Rp=reachable(o['rel'],o['states'].index(o['point']));RA=reachable(allops,o['states'].index(o['point']))
    def restrictions(M,R):return {tuple(f[i] for i in R) for f in M}
    member=tuple(p) in rel;memberALL=tuple(p) in ALL
    definition={'actor':B,'kind':'L_d' if B=='H' else 'M_d','initial_ref':o['initial_ref'],'certificate_ref':digest(cert),'table':p}
    key=B+'::'+digest(definition)+'::'+definition['kind'];new=not member and not memberALL
    extension=deepcopy(o['rel']);definitions=deepcopy(o['definitions'])
    if new:
        extension[key]=p;definitions[key]={'name':definition['kind'],'definition_ref':digest(definition),'installed_by':None}
    metrics={'REL_size':len(rel),'ALL_size':len(ALL),'REL_plus_size':len(closure(cp)),'ALL_plus_size':len(closure(ap)),
             'REL_member':member,'ALL_member':memberALL,'REL_word':rel.get(tuple(p)),'ALL_word':ALL.get(tuple(p)),
             'REL_maps':sorted(map(list,rel)),'ALL_maps':sorted(map(list,ALL)),
             'reachable_REL':[o['states'][j] for j in Rp],'reachable_ALL':[o['states'][j] for j in RA],
             'reachable_plus':[o['states'][j] for j in reachable(ap,o['states'].index(o['point']))],
             'new_reachable_map_REL':tuple(p[i] for i in Rp) not in restrictions(rel,Rp),
             'new_reachable_map_ALL':tuple(p[i] for i in RA) not in restrictions(ALL,RA),
             'new_endpoint':p[o['states'].index(o['point'])] not in RA,
             'atomic_selector_added':new,'verdict':'NEW FULL MAP' if new else 'DEFINABLE / NOT A NEW ATOM',
             'admissible_current_REL':member and 1<=len(rel[tuple(p)])<=3}
    return {'actor':B,'certificate':cert,'definition':definition,'candidate_key':key,'metrics':metrics,
            'rel_extension':extension,'definitions':definitions,'proposal_only':True,'enacted':False,
            'identity_inclusion':list(range(len(o['states']))),'preserved_point':deepcopy(o['point']),
            'old_signature_ref':digest(o['rel']),'structural_ref':o['initial_ref']}
