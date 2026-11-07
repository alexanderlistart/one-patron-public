"""Core-only structural constructors; no use of numeric internal coordinates."""
from copy import deepcopy
from location4 import digest

def perm(p):
    return isinstance(p,list) and len(p)==3 and all(type(x) is int for x in p) and sorted(p)==[0,1,2]

def indices(f,table):
    if len(table)!=len(f['states']) or any(s not in f['states'] for s in table):
        raise ValueError('PARTIAL_OWN_TABLE')
    return [f['states'].index(s) for s in table]

def closure(tables):
    n=len(tables[0]); identity=tuple(range(n)); seen={identity}; pending=[identity]
    while pending:
        a=pending.pop()
        for b in tables:
            c=tuple(b[a[i]] for i in range(n))
            if c not in seen: seen.add(c); pending.append(c)
    return sorted(map(list,seen))

def normalized(f):
    states=f['states']; beta=f['beta']; chi=f['embedding']
    if len(states)!=len({digest(x) for x in states}) or len(beta)!=len(states) or len(chi)!=3:
        raise ValueError('OWN_DOMAIN')
    t=[beta[states.index(s)] for s in chi]
    if not perm(t): raise ValueError('SECTION_REQUIRED')
    e=[states.index(chi[t.index(i)]) for i in range(3)]
    return e

def construct(actor,f,d):
    if f.get('status')!='PASS' or not perm(d): raise ValueError('TYPE_OR_D')
    states=f['states']; beta=f['beta']; e=normalized(f); n=len(states)
    ops={k:indices(f,v) for k,v in f['operations'].items()}
    out=[None]*n; normal=[]
    if actor=='H':
        T=ops['Turn']; U=ops['Advance']; lift='L_D'
        for i in range(3):
            row=[e[i],T[e[i]],T[T[e[i]]]]
            if len(set(row))!=3 or T[row[-1]]!=e[i] or any(beta[j]!=i for j in row):
                raise ValueError('H_NORMAL_FORM')
            for a,b in zip(row,[row[1],row[2],e[d[i]]]):
                if out[a] is not None: raise ValueError('H_OVERLAP')
                out[a]=b
            normal.append(row)
        oldnames=['Turn','Advance']; alias='Turn'; sections={'e':[states[j] for j in e]}
    elif actor=='A':
        S=ops['Seal']; R=ops['Readdress']; lift='M_D'; e0=[S[j] for j in e]
        for i in range(3):
            if e0[i]==e[i] or beta[e0[i]]!=i or S[e0[i]]!=e0[i]:
                raise ValueError('A_SECTIONS')
            for a,b in ((e0[i],e0[i]),(e[i],e0[d[i]])):
                if out[a] is not None: raise ValueError('A_OVERLAP')
                out[a]=b
            normal.append([e0[i],e[i]])
        oldnames=['Seal','Readdress']; alias='Seal'
        sections={'e0':[states[j] for j in e0],'e1':[states[j] for j in e]}
    else: raise ValueError('ACTOR')
    if any(s is None for s in out): raise ValueError('CARRIER_NOT_COVERED')
    old=closure([ops[k] for k in oldnames]); new=closure([ops[k] for k in oldnames]+[out])
    member=out in old; table=[deepcopy(states[j]) for j in out]
    operations=deepcopy(f['operations']); aliases={lift:alias} if out==ops[alias] else {}
    if not aliases: operations[lift]=table
    current=list(range(n)); order=None
    if sorted(out)==list(range(n)):
        for k in range(1,100):
            current=[out[j] for j in current]
            if current==list(range(n)): order=k; break
    return {'actor':actor,'states':deepcopy(states),'beta':deepcopy(beta),'chi':deepcopy(f['embedding']),
            'sections':sections,'normal_forms':[[states[j] for j in row] for row in normal],
            'lift_name':lift,'lift_table':table,'operations':operations,'aliases':aliases,
            'novelty':{'status':'ALIAS / NO NEW OWN OPERATOR' if member else 'NEW OWN OPERATOR',
                       'lift_old_member':member,'old_word_maps':old,'new_word_maps':new,
                       'old_size':len(old),'new_size':len(new),'order':order,
                       'rank':len(set(out)),'idempotent':[out[j] for j in out]==out},
            'source_definition_ref':digest(f),'scope':'finite own language; NOT E2'}

def naturality(actor,f,d):
    src=construct(actor,f,d); n=len(f['states']); width=3 if actor=='H' else 2
    patterns=([[1,2,0],[0,2,1],[2,1,0]] if actor=='H' else [[1,0],[0,1],[1,0]])
    rows=[]
    for g in ([0,1,2],[1,0,2]):
        fibres=[[j for j,b in enumerate(f['beta']) if b==i] for i in range(3)]
        fmap=[None]*n
        for i in range(3):
            if len(fibres[i])!=width: raise ValueError('FIBRE_CARDINALITY')
            for z,j in enumerate(fibres[i]): fmap[j]=fibres[g[i]][patterns[i][z]]
        inv=[fmap.index(i) for i in range(n)]; gi=[g.index(i) for i in range(3)]
        target=deepcopy(f)
        target['beta']=[g[f['beta'][inv[j]]] for j in range(n)]
        target['embedding']=[f['states'][fmap[f['states'].index(f['embedding'][gi[i]])]] for i in range(3)]
        target['trace']=[target['beta'][target['states'].index(s)] for s in target['embedding']]
        for name,t in f['operations'].items():
            ix=indices(f,t)
            target['operations'][name]=[f['states'][fmap[ix[inv[j]]]] for j in range(n)]
        dp=[g[d[gi[i]]] for i in range(3)]
        rebuilt=construct(actor,target,dp); left=[fmap[j] for j in indices(f,src['lift_table'])]
        out=indices(target,rebuilt['lift_table']); right=[out[j] for j in fmap]
        if left!=right: raise ValueError('NATURALITY')
        rows.append({'g':g,'own_bijection':fmap,'d_prime':dp,'left':left,'right':right,'equal':True})
    return {'status':'PASS','scope':'representation isomorphism, not own historical change','cases':rows}
