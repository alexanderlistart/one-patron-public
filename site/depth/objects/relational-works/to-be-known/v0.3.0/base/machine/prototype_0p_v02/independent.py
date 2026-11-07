"""Independent v0.2 replay; NEVER imports continuing.py or original core.py."""
from copy import deepcopy
from itertools import product
from environment import digest
import verifier as prior

TRIANGLE=[[0,1],[1,2],[2,0]]
CONTEXT_ID="H1:E1:operations-completed"

def transport(p, path, x):
    for start,end in path:
        found=False
        for edge,mapping in zip(p["graph"],p["transports"]):
            if edge==[start,end]:
                x=mapping[x]; found=True; break
            if edge==[end,start]:
                x=prior.inv_map(mapping)[x]; found=True; break
        if not found:
            raise ValueError("missing edge")
    return x

def calculate_next(genesis,e):
    a=next(row for row in genesis["events"] if row["id"]=="A1")
    r=next(row for row in genesis["events"] if row["id"]=="R0")
    a_map,h_map,r_map=a["payload"]["trace"],e["payload"]["trace"],r["payload"]["map"]
    b,c,_,_=prior.algebra(a_map,h_map,r_map)
    graph=e["payload"].get("structure",{}).get("to",TRIANGLE)
    if graph not in (TRIANGLE,TRIANGLE[:2]):
        raise ValueError("FACTOR_PROFILE")
    psi={"version":"Psi/2","parent":"Psi/1","graph":graph,
         "transports":[c if edge==[2,0] else [0,1,2] for edge in graph],
         "a":a_map,"h":h_map,"r":r_map,"b":b,"trace_commutator":c,
         "refs":{"a":a["id"],"h":e["id"],"r":r["id"]},"Lost":e["payload"]["Lost"]}
    psi["monodromy"]=[transport(psi,TRIANGLE,x) for x in range(3)] if set(map(tuple,TRIANGLE))<=set(map(tuple,graph)) else None
    assignments=[]
    for row in product(range(3),repeat=3):
        if all(transport(psi,[edge],row[edge[0]])==row[edge[1]] for edge in graph):
            assignments.append(list(row))
    psi["sections"]=assignments
    m=psi["monodromy"]
    psi["cyclic"]=bool(m is not None and all(m[i]!=i for i in range(3)) and
                         all(m[m[m[i]]]==i for i in range(3)))
    return psi

def judge_bridge(old,new,w,e,admitted):
    empty={"strict":"INSUFFICIENT EVIDENCE","historical":"INSUFFICIENT EVIDENCE","squares":[]}
    if not admitted or w is None:
        return empty
    if (w.get("from"),w.get("to"),w.get("source_event_ref"))!=("Psi/1","Psi/2",e["id"]) or not prior.bijection(w.get("vertices")) or not isinstance(w.get("phi"),list) or len(w["phi"])!=3 or not all(prior.bijection(p) for p in w["phi"]):
        return {"strict":"OBSTRUCTED","historical":"INSUFFICIENT EVIDENCE","squares":[]}
    rows=[]
    for edge,t in zip(old["graph"],old["transports"]):
        u,v=edge
        path=w.get("paths",{}).get(str(u)+"-"+str(v))
        if path is None:
            return {"strict":"NOT TRANSPORTABLE","historical":"NOT TRANSPORTABLE","squares":rows}
        at=w["vertices"][u]
        for source,target in path:
            if source!=at:
                return {"strict":"OBSTRUCTED","historical":"OBSTRUCTED","squares":rows}
            at=target
        if at!=w["vertices"][v]:
            return {"strict":"OBSTRUCTED","historical":"OBSTRUCTED","squares":rows}
        try:
            left=[w["phi"][v][t[x]] for x in range(3)]
            right=[transport(new,path,w["phi"][u][x]) for x in range(3)]
        except ValueError:
            return {"strict":"NOT TRANSPORTABLE","historical":"NOT TRANSPORTABLE","squares":rows}
        rows.append({"edge":edge,"path":path,"left":left,"right":right,"commutes":left==right})
    preserved=all(row["commutes"] for row in rows)
    lawful_change=(w.get('allow_transport_change') and old['graph']==new['graph'] and w['vertices']==[0,1,2]
                   and w['phi']==[[0,1,2]]*3 and w['paths']=={'0-1':[[0,1]],'1-2':[[1,2]],'2-0':[[2,0]]}
                   and old['transports']!=new['transports'])
    return {"strict":"PRESERVED" if preserved else "OBSTRUCTED",
            "historical":"PRESERVED" if preserved else "TRANSFORMED" if lawful_change else "OBSTRUCTED",
            "squares":rows}

class Ledger:
    def __init__(self,head):
        self.records=[]; self.head=head
    def add(self,kind,payload):
        entry={"seq":len(self.records),"branch":"H1/continuing","previous":self.head,
               "kind":kind,"policy":"E1","payload":deepcopy(payload)}
        entry["digest"]=digest(entry)
        self.records.append(entry); self.head=entry["digest"]

def replay(genesis,scenario,base):
    if prior.verify(base,genesis)["status"]!="PASS":
        raise ValueError("invalid v0.1 prefix")
    branch=base["branches"]["H1"]
    if branch["active_policy"]!="E1" or len(branch["operations"])!=5:
        raise ValueError("executed E1 absent")
    p1=deepcopy(branch["psi"])
    records={e["id"]:e for e in genesis["events"]}
    ids=[e["id"] for e in genesis["events"]]+["h1",CONTEXT_ID]
    h_ids=["H0","C0","h1"]
    install=[e for e in branch["journal"] if e["kind"]=="Install"][0]
    executions=[e for e in branch["journal"] if e["kind"]=="Reverse"]
    context={"id":CONTEXT_ID,"install_ref":install["digest"],"execution_ref":executions[-1]["digest"],
             "psi1_digest":digest(p1),"old_verdict_digest":digest(branch["global"]),
             "policy":"E1","active_ids":deepcopy(ids),"H_history":deepcopy(h_ids)}
    ledger=Ledger(branch["journal"][-1]["digest"])
    ledger.add("ContinuationContext",context)
    before=deepcopy({"context":context,"journal":ledger.records})
    trace=[]; p2=None; current="Psi/1"; issued=set()
    def iscyclic(p):
        m=p.get("monodromy") if "monodromy" in p else p["c"]
        return p["graph"]==TRIANGLE and m is not None and all(m[i]!=i for i in range(3)) and all(m[m[m[i]]]==i for i in range(3))
    def token(psi,k=0,x0=0):
        p=p1 if psi=="Psi/1" else p2
        m=p["c"] if psi=="Psi/1" else p["monodromy"]
        x=x0
        for _ in range(k//3):
            x=m[x]
        value={"psi":psi,"psi_digest":digest(p),"policy":"E1",
               "state":{"k":k,"q":k//3,"vertex":k%3,"x":x},"x0":x0}
        issued.add(digest(value))
        return value
    def query(op,psi,mode="current",tok=None,policy="E1"):
        p=p1 if psi=="Psi/1" else p2 if psi=="Psi/2" else None
        req={"op":op,"psi":psi,"mode":mode,"policy":policy,"token":deepcopy(tok)}
        if policy!="E1":
            ans={"status":"FAIL","reason":"STALE_POLICY"}
        elif p is None:
            ans={"status":"BLOCKED","reason":"NO_PSI"}
        elif mode not in ("current","historical"):
            ans={"status":"FAIL","reason":"MODE"}
        elif mode=="current" and psi!=current:
            ans={"status":"FAIL","reason":"STALE_PSI"}
        elif tok and (tok.get("psi")!=psi or tok.get("psi_digest")!=digest(p) or tok.get("policy")!=policy):
            ans={"status":"FAIL","reason":"STALE_STATE_SCOPE"}
        elif tok and digest(tok) not in issued:
            ans={"status":"FAIL","reason":"UNISSUED_STATE"}
        elif op=="GlobalJoin":
            sections=p["sections"] if psi=="Psi/2" else [[x,x,x] for x in p["fixed"]]
            ans={"status":"PASS" if sections else "FAIL","reason":"GLOBAL_SECTION" if sections else "GLOBAL_SECTION_OBSTRUCTED",
                 "sections":sections,"policy":"E1","psi":psi}
        elif op=="Cyclic":
            ans={"status":"PASS","token":token(psi)} if iscyclic(p) else {"status":"BLOCKED","reason":"CYCLIC_NOT_APPLICABLE"}
        elif op=="Return":
            if not iscyclic(p):
                ans={"status":"BLOCKED","reason":"CYCLIC_NOT_APPLICABLE"}
            elif not tok:
                ans={"status":"FAIL","reason":"STATE_REQUIRED"}
            elif token(psi,tok["state"]["k"],tok["x0"])!=tok:
                ans={"status":"FAIL","reason":"STATE_INVARIANT"}
            else:
                k=tok["state"]["k"]; v=k%3
                path=[[v,(v+1)%3],[(v+1)%3,(v+2)%3],[(v+2)%3,v]]
                x=transport(p,path,tok["state"]["x"])
                after=token(psi,(k+3)%9,tok["x0"])
                if x!=after["state"]["x"]:
                    raise ValueError("return invariant")
                ans={"status":"PASS","transition":{"path":path,"before":tok["state"],"after":after["state"]},"token":after}
        else:
            ans={"status":"FAIL","reason":"UNKNOWN_OPERATION"}
        row={"request":req,"response":ans}; trace.append(deepcopy(row)); ledger.add("Operation",row)
        return ans
    original=query("Cyclic","Psi/1")["token"]
    pre_token=query("Return","Psi/1",tok=original)["token"]
    e=deepcopy(scenario["event"]); w=deepcopy(scenario.get("bridge"))
    ledger.add("RecordedCandidate",e)
    source=e.get("source")=="H" and e.get("kind") in ("HServiceAfterE1","HStructuralChangeAfterE1","HRevisionOrPause")
    parents=e.get("parents",[])
    linked=(isinstance(parents,list) and {"h1","C0",CONTEXT_ID}<=set(parents) and
            set(parents)<=set(ids) and e.get("id") not in ids and e.get("payload",{}).get("covenant_ref")=="C0")
    origin=e.get("origin")=="AUTHORED PREMISE"
    pause=e.get("kind")=="HRevisionOrPause"
    math=True if pause else prior.check_bridge(e)
    structure=e.get("payload",{}).get("structure")
    structok=(not structure or e.get("kind")=="HStructuralChangeAfterE1" and structure.get("from")==TRIANGLE and structure.get("to")==TRIANGLE[:2] and bool(structure.get("reason")))
    if e.get("kind")=="HStructuralChangeAfterE1" and not structure:
        structok=False
    status="FAIL" if not source or not linked or not math or not structok else "UNRESOLVED" if not origin else "PASS"
    admission={"status":status,"origin":"AUTHORED PREMISE" if origin else "UNRESOLVED",
               "source":"STRUCTURALLY VERIFIED" if source and linked else "FAIL",
               "covenant_ref":"C0","eta_acceptance_ref":"C0",
               "reason":"H_PAUSE" if status=="PASS" and pause else "H_OWNED_AFTER_EXECUTED_E1" if status=="PASS" else "SOURCE_OR_CONTEXT"}
    ledger.add("Admission",admission)
    candidate=calculate_next(genesis,e) if not pause and math and structok else None
    if status=="PASS":
        ids.append(e["id"]); h_ids.append(e["id"])
        if not pause:
            p2=deepcopy(candidate); current="Psi/2"; ledger.add("PsiVersion2",p2)
    bridge=judge_bridge(p1,p2,w,e,p2 is not None) if p2 else {"strict":"INSUFFICIENT EVIDENCE","historical":"INSUFFICIENT EVIDENCE","squares":[]}
    ledger.add("BridgeJudgements",bridge)
    query("GlobalJoin","Psi/2")
    query("Cyclic","Psi/2")
    query("Return","Psi/2")
    query("Return","Psi/2",tok=pre_token)
    query("Return","Psi/1",mode="historical",tok=pre_token)
    query("Return","Psi/1",mode="current",tok=pre_token)
    query("GlobalJoin",current,policy="E0")
    transferable=(p2 and bridge["strict"]=="PRESERVED" and w["vertices"]==[0,1,2] and w["phi"]==[[0,1,2]]*3
                  and w["paths"]=={"0-1":[[0,1]],"1-2":[[1,2]],"2-0":[[2,0]]})
    transfer={"status":"PASS","token":token("Psi/2",pre_token["state"]["k"],pre_token["x0"])} if transferable else {
        "status":"OBSTRUCTED" if bridge["strict"]=="OBSTRUCTED" else "NOT TRANSPORTABLE" if bridge["strict"]=="NOT TRANSPORTABLE" else "INSUFFICIENT EVIDENCE"}
    ledger.add("ExplicitStateTransfer",{"input":pre_token,"result":transfer})
    if transfer["status"]=="PASS":
        query("Return","Psi/2",tok=transfer["token"])
    return {"schema":"source-x-continuing/2","before":before,"context":context,"candidate":e,
            "admission":admission,"math_candidate":candidate,"active_ids":ids,"H_history":h_ids,
            "psi1":p1,"psi2":p2,"current":current,"policy":"E1",
            "old_E0_verdict":deepcopy(branch["global"]),"covenant":deepcopy(records["C0"]),
            "bridge":bridge,"proposal":w,"trace":trace,"transfer":transfer,"journal":ledger.records,
            "formal_novelty_against_E0plus":"FAIL",
            "unresolved":["r-origin","H-2","personal/numerical identity","Strong CO-EVOLVE","X4"]}

def differences(a,b,prefix=""):
    if type(a)!=type(b):
        return [prefix+": type"]
    if isinstance(a,dict):
        if set(a)!=set(b):
            return [prefix+": keys"]
        out=[]
        for key in a: out.extend(differences(a[key],b[key],prefix+"/"+str(key)))
        return out
    if isinstance(a,list):
        if len(a)!=len(b): return [prefix+": length"]
        out=[]
        for i,(x,y) in enumerate(zip(a,b)): out.extend(differences(x,y,prefix+"/"+str(i)))
        return out
    return [] if a==b else [prefix]

def verify(artifact,genesis,scenario,base):
    try:
        expected=replay(genesis,scenario,base)
        errors=differences(artifact,expected)
    except (ValueError,KeyError,TypeError,IndexError) as exc:
        errors=["malformed/prefix: "+str(exc)]
    return {"status":"PASS" if not errors else "FAIL","problems":errors[:80],
            "scope":"conditional authored provenance / structural and operational verification",
            "unresolved":["r-origin","H-2","personal/numerical identity","Strong CO-EVOLVE","X4"]}

def verify_bundle(bundle,genesis,future):
    problems=[]; results={}
    try:
        if bundle['schema']!='source-x-continuing-bundle/2' or bundle['genesis_digest']!=digest(genesis) or bundle['future_digest']!=digest(future):
            problems.append('bundle/pinned inputs')
        if set(bundle['cases'])!=set(future['cases']): problems.append('case inventory')
        for name,scenario in future['cases'].items():
            result=verify(bundle['cases'][name],genesis,scenario,bundle['base'])
            results[name]=result
            if result['status']!='PASS': problems.append(name)
            own=replay(genesis,scenario,bundle['base'])
            if bundle['admission_boundary']!=own['before']: problems.append('future input leakage/boundary')
    except (ValueError,KeyError,TypeError,IndexError) as exc:
        problems.append('malformed bundle: '+str(exc))
    return {'status':'PASS' if not problems else 'FAIL','problems':problems,'cases':results,
            'scope':'STRUCTURALLY VERIFIED / INFERRED RESULT conditional on AUTHORED PREMISE'}

if __name__=='__main__':
    import argparse
    import sys
    from environment import ROOT, load, encode
    parser=argparse.ArgumentParser()
    parser.add_argument('--bundle',required=True)
    args=parser.parse_args()
    result=verify_bundle(load(args.bundle),load(ROOT/'fixtures/genesis.json'),load(ROOT/'fixtures/continuations.json'))
    print(encode(result).decode(),end='')
    sys.exit(0 if result['status']=='PASS' else 1)

