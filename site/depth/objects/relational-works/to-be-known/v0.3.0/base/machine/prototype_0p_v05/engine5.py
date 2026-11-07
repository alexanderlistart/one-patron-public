"""Finite authored continuation; independent admission precedes every commit."""
from copy import deepcopy
from functools import lru_cache
from collections import Counter
from support5 import ROOT,OLD,load,digest,integrity,plans,static_choices
import algebra5 as math
import core4 as previous

SEM='already-refined/0.5'
LIMITS={'Strong CO-EVOLVE':'UNRESOLVED','X4':'UNRESOLVED','H-2':'UNRESOLVED','r-origin':'UNRESOLVED',
        'external subjectivity/consciousness/free will':'UNRESOLVED','personal/numerical identity':'UNRESOLVED','C7':'UNRESOLVED'}
PROFILE={'ordinary':'R','word_policy':'W1','REL_bound':[1,3],'mixed':False,'install':'Own PROPOSAL after independent admission',
         'ordinary_REL_install':False,'partial_local_actual':'OUT OF SCOPE','joint_policy':'E1'}

@lru_cache(maxsize=1)
def old_replay():
    integrity();a=previous.kernel()
    if a!=load(OLD[0]/'evidence/final1/core_evidence.json'):raise ValueError('OLD_REPLAY_IDENTITY')
    return a
def past_ids(a):
    result=set()
    def visit(z):
        if isinstance(z,dict):
            if 'kind' in z and isinstance(z.get('id'),str):result.add(z['id'])
            for v in z.values():visit(v)
        elif isinstance(z,list):
            for v in z:visit(v)
    visit(a);return result
def seed(a,name):
    if name not in ('H-T','H-A','A-S','A-R'):raise ValueError('SEED_SCOPE')
    first=a['generation1']['branches'][name];second=a['branches'][name];actors={}
    for B in ('A','H'):
        native=first if first['event']['actor']==B else second;f=a['generation1']['contexts'][B]['formation'];ref=digest(f)
        st=deepcopy(f['states']);keys={};rel={};definitions={}
        for display,table in native['after']['operations'].items():
            origin=ref if display in f['operations'] else second['formation_ref']
            key=B+'::'+origin+'::'+display;keys[display]=key;rel[key]=[st.index(x) for x in table]
            definitions[key]={'name':display,'definition_ref':origin,'installed_by':native['event']['id']}
        word=[keys[native['event']['selected_operation']]] if native is first else [keys[s['resolved']] for s in native['own_steps']]
        o={'actor':B,'states':st,'I':[0,1,2],'J':[0,1,2],'input':1,'kappa':[0,1,2],
           'interface_scope':B+'/I','input_scope':B+'/J/'+ref,'beta':deepcopy(f['beta']),'chi':deepcopy(f['embedding']),
           'initial_ref':ref,'names':keys,'rel':rel,'definitions':definitions,'marks':[],
           'point':deepcopy(f['embedding'][1]),'sigma':deepcopy(f['embedding']),
           'path':[],'ordinary_key':B+'::Ordinary_R_Q_delta/0.5','ordinary_delta':[1,0,2],
           'law_version':native['after']['law'],'state_version':digest(native['after']),
           'source_event_ref':digest(native['event'])}
        o['marks']=[[deepcopy(st[j]) for j in row] for row in math.normals(o)]
        executed=math.apply(o,word)
        rows=native['composition']['rows'];saved=[r['operated'] if native is first else r['states'][-1] for r in rows]
        if executed['sigma']!=saved or executed['point']!=native['after']['value'] or executed['cumulative']!=native['effective_trace']:
            raise ValueError('SEED_OWN_REPLAY')
        o.update(point=executed['point'],sigma=executed['sigma'])
        o['path']=[{'id':native['event']['id'],'source':B,'event_ref':digest(native['event']),
                    'word':word,'steps':executed['steps'],'origin':'ACTUAL PRIOR AUTHORED EVENT'}]
        math.frame_replay(o);actors[B]=o
    hist=a['generation1']['prefix']['histories']['alpha'];p=hist['prefix']
    witness={'W':deepcopy(a['generation1']['contexts']['H']['W']),'old':deepcopy(p['psi1']),
             'target':deepcopy(p['psi2']),'proposal':deepcopy(p['proposal']),'event':deepcopy(p['candidate']),
             'ell':deepcopy(hist['address_map'])}
    return {'seed':name,'actors':actors,'Psi':deepcopy(second['Psi2']),'witness':witness,
            'history_head':second['journal'][-1]['digest'],'accepted_ids':[],
            'historical_ref':digest(a),'policy':'E1','covenant_ref':'C0','eta_acceptance_ref':'C0','profile':deepcopy(PROFILE)}
def prepare(w,B,slot):
    P=math.proposal(w,B)
    ctx={'slot':slot,'actor':B,'world_ref':digest(w),'own_ref':digest(w['actors'][B]),
         'own_version':w['actors'][B]['state_version'],'Psi_parent':digest(w['Psi']),
         'history_parent':w['history_head'],'formation_ref':digest(P),'input_scope':w['actors'][B]['input_scope'],
         'policy':'E1','profile':deepcopy(PROFILE)}
    return {'context':ctx,'formation':P}
def evaluate(w,prepared,event,forbidden):
    result={'status':'WAIT','accepted':False,'reason':'NO_EVENT','event':deepcopy(event),'own_steps':[],
            'sigma_before':None,'sigma_next':None,'cumulative':None,'relative':None,'rows':[],
            'next_actor':None,'next_Psi':None,'joint_trace':[],'installation':None}
    if event is None:return result
    ctx=prepared['context'];P=prepared['formation'];B=ctx['actor'];o=w['actors'][B];e=event
    def reject(reason):
        result.update(status='REJECTED',reason=reason,installation=None,next_actor=None,next_Psi=None)
        return result
    expected={'id','kind','actor','source','origin','covenant_ref','eta_acceptance_ref','context_ref','formation_ref',
              'before_ref','before_version','Psi_parent','history_parent','input_scope','action','mode','word'}
    if set(e)!=expected or e['kind']!='OwnContinuation05':return reject('EVENT_SCHEMA')
    if type(e['id']) is not str or not e['id'] or e['id'] in forbidden or e['id'] in w['accepted_ids'] or e['id'] in {'C0','eta'}:return reject('EVENT_ID')
    if e['actor']!=B or e['source']!=B:return reject('ACTOR_SOURCE')
    if e['origin']!='AUTHORED PREMISE':return reject('UNRESOLVED_ORIGIN')
    if e['covenant_ref']!='C0' or e['eta_acceptance_ref']!='C0':return reject('COVENANT')
    if e['before_ref']!=digest(o) or e['before_version']!=o['state_version']:return reject('STALE_OWN_BEFORE')
    if e['Psi_parent']!=digest(w['Psi']):return reject('STALE_PSI_PARENT')
    if e['history_parent']!=w['history_head'] or e['context_ref']!=digest(ctx) or e['formation_ref']!=digest(P) or e['input_scope']!=o['input_scope']:
        return reject('STALE_CONTEXT_OR_FORMATION')
    if e['action'] not in ('Own','Ordinary','Pause') or e['mode'] not in ('CURRENT','PROPOSAL') or type(e['word']) is not list:return reject('ACTION_SCHEMA')
    if e['action'] in ('Ordinary','Pause') and (e['mode']!='CURRENT' or e['word']):return reject('NON_OWN_WORD_OR_INSTALL')
    if e['action']=='Pause':result.update(status='PAUSE',accepted=True,reason='LAWFUL_PAUSE');return result
    try:
        math.frame_replay(o);new=deepcopy(o)
        if e['action']=='Ordinary':
            word=[o['ordinary_key']];ops={word[0]:math.ordinary(o)}
        else:
            word=e['word']
            if not 1<=len(word)<=3:return reject('WORD_LENGTH')
            if any(k==o['ordinary_key'] or 'Ordinary' in str(k) for k in word):return reject('MIXED_FAMILY')
            ops=o['rel'] if e['mode']=='CURRENT' else P['rel_extension']
            if any(k not in ops for k in word):return reject('OPERATOR_OR_ALIAS_NOT_ADMITTED')
            if e['mode']=='PROPOSAL':
                new['rel']=deepcopy(P['rel_extension']);new['definitions']=deepcopy(P['definitions'])
                for k in set(new['rel'])-set(o['rel']):new['definitions'][k]['installed_by']=e['id']
                new['law_version']='local/0.5/'+digest(P)
                result['installation']={'from':o['law_version'],'to':new['law_version'],'event':e['id'],
                                        'added':sorted(set(new['rel'])-set(o['rel'])),'formation_ref':digest(P)}
        t=math.apply(o,word,ops=ops)
        if not math.permutation(t['cumulative']):return reject('CUMULATIVE_NOT_S3')
        new.update(point=t['point'],sigma=t['sigma'],source_event_ref=digest(e))
        new['path'].append({'id':e['id'],'source':B,'event_ref':digest(e),'word':word,'steps':t['steps'],'origin':'ACCEPTED OWN EVENT' if e['action']=='Own' else 'ACCEPTED ORDINARY EVENT'})
        new['state_version']=digest({'before':digest(o),'event':digest(e),'point':new['point'],'sigma':new['sigma'],'law':new['law_version']})
        # Ordinary words stay separate from REL; history replay resolves Q by its rule.
        q=math.mul(t['cumulative'],math.inverse(o['kappa']));other=w['actors']['H' if B=='A' else 'A']
        other_t=[other['beta'][other['states'].index(s)] for s in other['sigma']]
        other_q=math.mul(other_t,math.inverse(other['kappa']))
        p=math.relation(q if B=='A' else other_q,q if B=='H' else other_q,w['Psi']['r'])
        p.update(version='Psi/0.5/'+e['id'],parent_ref=digest(w['Psi']),event_ref=digest(e),policy='E1')
        result.update(status='ACCEPTED',accepted=True,reason='OWN_ENACTED' if e['action']=='Own' else 'ORDINARY_ENACTED',
                      own_steps=t['steps'],sigma_before=deepcopy(o['sigma']),sigma_next=t['sigma'],cumulative=t['cumulative'],
                      relative=math.mul(t['cumulative'],math.inverse([o['beta'][o['states'].index(s)] for s in o['sigma']])),
                      rows=t['rows'],next_actor=new,next_Psi=p,joint_trace=math.joint(p,w['Psi']))
    except (ValueError,KeyError,TypeError,IndexError) as exc:return reject(str(exc))
    return result
def commit(w,preview):
    new=deepcopy(w)
    if not preview['accepted']:return new,None
    e=preview['event'];entry={'seq':len(w['accepted_ids']),'previous':w['history_head'],
                            'kind':'Pause' if preview['status']=='PAUSE' else 'AcceptedContinuation','payload':deepcopy(preview)}
    entry['digest']=digest(entry);new['history_head']=entry['digest'];new['accepted_ids'].append(e['id'])
    if preview['next_actor'] is not None:
        new['actors'][e['actor']]=deepcopy(preview['next_actor']);new['Psi']=deepcopy(preview['next_Psi'])
    return new,entry
def build(choice_loader=static_choices):
    integrity();a=old_replay();layout=plans();initials={};first_prepared={}
    for name,c in sorted(layout.items()):
        initials[name]=seed(a,c['seed']);first_prepared[name]=prepare(initials[name],c['actors'][0],name+'/0')
    choices=choice_loader(deepcopy(first_prepared)) or {}
    events=[e for es in choices.values() for e in es if e is not None]
    counts=Counter(e.get('id') for e in events if type(e.get('id')) is str);blocked=past_ids(a)|{i for i,n in counts.items() if n>1}
    import independent5 as independent
    ia=independent.old_replay();trials={}
    for name,c in sorted(layout.items()):
        w=deepcopy(initials[name]);iw=independent.seed(ia,c['seed'])
        if w!=iw:raise ValueError('INDEPENDENT_SEED')
        stages=[];ledger=[]
        for i,B in enumerate(c['actors']):
            if i and not stages[-1]['preview']['accepted']:
                stages.append({'slot':name+'/'+str(i),'blocked':'DEPENDENCY_NOT_ACCEPTED','event':None});break
            p=prepare(w,B,name+'/'+str(i));es=choices.get(name,[]);e=deepcopy(es[i]) if i<len(es) else None
            preview=evaluate(w,p,e,blocked)
            checked=independent.check_admission(w,p,e,blocked,preview)
            if checked['status']!='PASS':
                preview={'status':'REJECTED','accepted':False,'reason':'INDEPENDENT_ADMISSION','event':e,
                         'own_steps':[],'sigma_before':None,'sigma_next':None,'cumulative':None,'relative':None,
                         'rows':[],'next_actor':None,'next_Psi':None,'joint_trace':[],'installation':None}
            after,entry=commit(w,preview)
            stages.append({'slot':name+'/'+str(i),'before':deepcopy(w),'prepared':p,'event':e,'preview':preview,
                           'independent_admission':checked,'after':deepcopy(after),'ledger_entry':entry})
            if entry:ledger.append(entry)
            w=after
        trials[name]={'seed':c['seed'],'initial':initials[name],'stages':stages,'accepted_ledger':ledger,'final':w}
    return {'schema':SEM,'profile':deepcopy(PROFILE),'historical':a,'trials':trials,
            'formal_novelty_against_E0plus':'FAIL','limits':deepcopy(LIMITS),
            'scope':'finite authored already-refined continuation; no external identity claim'}
def kernel():return build()
