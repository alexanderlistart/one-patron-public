"""Independent NEW O/chi/beta semantics. No action_core imports."""
from copy import deepcopy
from itertools import permutations
from location_a import digest,load,V01,V02,V03,ROOT
import own_checker as prior
import verifier as pointwise

SEM="operation-semantics/0.3a"
LIMITS=["r-origin","H-2","personal/numerical identity","Strong CO-EVOLVE","X4"]

class Ledger:
    def __init__(self,actor,head): self.actor=actor; self.head=head; self.rows=[]
    def add(self,kind,payload):
        x={"seq":len(self.rows),"branch":"selected-own/"+self.actor,"previous":self.head,
           "kind":kind,"policy":"E1","payload":deepcopy(payload)}
        x["digest"]=digest(x); self.rows.append(x); self.head=x["digest"]

def replay_context(g,c,f):
    prefix=prior.replay(g,c,{"schema":f["schema"],"histories":f["histories"]},{})
    h=prefix["histories"]["alpha"]; snap=prefix["snapshots"]["alpha"]
    ctx={actor:{"semantic_version":SEM,"actor":actor,"history_ref":digest(h),"history_head":h["journal"][-1]["digest"],
         "W":prefix["witnesses"]["alpha"],"formation":prefix["formations"]["alpha"][actor],"before":snap[actor],
         "r":snap["interfaces"]["r"],"other_trace":snap["H" if actor=="A" else "A"]["trace"],
         "policy":"E1","graph":snap["Psi"]["graph"],"anchor":0,"orientation":[[0,1],[1,2],[2,0]],
         "covenant":h["covenant"],"old_E0_verdict":h["old_E0_verdict"]} for actor in ("A","H")}
    return prefix,ctx

def evaluate(f,selected,domain):
    if f.get("status")!="PASS" or selected not in f.get("operations",{}): raise ValueError("OPERATION_NOT_IN_OWN_TYPE")
    states=f["states"]; outputs=f["operations"][selected]
    if (domain!=[0,1,2] or len(states)!=len(set(map(tuple,states))) or len(f["beta"])!=len(states) or
        len(outputs)!=len(states) or len(f["embedding"])!=len(domain) or
        any(type(i) is not int or i not in domain for i in f["beta"]) or
        any(x not in states for x in outputs+f["embedding"])):
        raise ValueError("PARTIAL_OR_ILL_TYPED_FUNCTION")
    beta=dict(zip(map(tuple,states),f["beta"]))
    operation=dict(zip(map(tuple,states),outputs))
    chi=dict(zip(domain,f["embedding"]))
    rows=[]
    for i in domain:
        embedded=chi[i]; moved=operation[tuple(embedded)]
        rows.append({"input":i,"embedded":embedded,"operated":moved,"projected":beta[tuple(moved)]})
    effective=[r["projected"] for r in rows]
    valid=set(effective)=={0,1,2} and len(effective)==3 and all(type(x) is int for x in effective)
    return {"rows":rows,"effective_trace":effective,"s3_status":"PASS" if valid else "FAIL"}

def relation(a,h,r):
    b,c,n,fixed=pointwise.algebra(a,h,r)
    return {"a":a,"h":h,"r":r,"b":b,"c":c,"graph":[[0,1],[1,2],[2,0]],"transports":[[0,1,2],[0,1,2],c],
            "order":n,"fixed":fixed,"sections":[[x]*3 for x in fixed],
            "capabilities":["GlobalJoin"] if fixed else ["Cyclic","Path","Reverse","Return"]}

def joint_trace(p,policy):
    scope=digest(p)
    if p["fixed"]:
        return [{"request":{"op":"GlobalJoin","policy":policy,"scope":scope},
                 "response":{"status":"PASS","section":p["sections"][0]}}]
    if policy!="E1" or p["order"]!=3: raise ValueError("joint profile")
    k,vertex,x=0,0,0
    def token(): return {"policy":"E1","scope":scope,"state":{"k":k,"q":k//3,"vertex":vertex,"x":x},"x0":0}
    rows=[{"request":{"op":"FormCyclic","policy":"E1","scope":scope},"response":{"status":"PASS","token":token()}}]
    for op in ("Path","Reverse","Return","Return","Return"):
        initial=token(); before=deepcopy(initial["state"])
        request_path=[[0,1]] if op in ("Path","Reverse") else None
        path=[[0,1]] if op=="Path" else [[1,0]] if op=="Reverse" else [[0,1],[1,2],[2,0]]
        for u,v in path:
            if u!=vertex: raise ValueError("path source")
            if v==(u+1)%3: mapping=p["transports"][u]; k=(k+1)%9
            else: mapping=pointwise.inv_map(p["transports"][v]); k=(k-1)%9
            x=mapping[x]; vertex=v
        step={"path":path,"before":before,"after":deepcopy(token()["state"])}
        rows.append({"request":{"op":op,"token":initial,"path":request_path},
                     "response":{"status":"PASS","transition":step,"token":token()}})
    return rows

def execute_expected(ctx,e):
    actor=ctx["actor"]; f=ctx["formation"]
    log=Ledger(actor,ctx["history_head"]); log.add("Context",ctx); log.add("Formation",f)
    out={"semantic_version":SEM,"context_ref":digest(ctx),"event":None,"status":"NOT ENACTED","own_status":"NOT ENACTED",
         "interface_status":"NOT EVALUATED","before":deepcopy(ctx["before"]),"after":deepcopy(ctx["before"]),
         "formation_trace":deepcopy(f.get("trace")),"effective_trace":None,"composition":None,"feedback":None,"joint_trace":[],
         "covenant_ref":"C0","eta_acceptance_ref":"C0","policy":"E1","unresolved":LIMITS}
    if e is not None:
        e=deepcopy(e); out["event"]=e; log.add("AuthoredChoice",e)
        expected={"id","kind","actor","source","origin","context","formation","action","selected_operation"}
        valid=(set(e)==expected and type(e["id"]) is str and bool(e["id"]) and e["id"] not in {"A0","A1","H0","C0","R0","h1"} and
               (e["kind"],e["actor"],e["source"],e["context"],e["formation"])==("OwnEnactment03a",actor,actor,"alpha:own:"+actor,"alpha:formation:"+actor)
               and e["action"] in ("relational","Ordinary","Pause"))
        if not valid: out.update(status="FAIL",reason="OWN_SOURCE_OR_SCHEMA")
        elif e["origin"]!="AUTHORED PREMISE": out.update(status="UNRESOLVED",reason="OWN_ORIGIN")
        elif e["action"]!="relational" and e["selected_operation"] is not None: out.update(status="FAIL",reason="SELECTOR_NOT_APPLICABLE")
        elif e["action"]=="Pause": out.update(status="PASS",reason="PAUSE")
        elif e["action"]=="Ordinary":
            out["after"]["value"]=ctx["before"]["trace"][ctx["before"]["value"]]
            out.update(status="PASS",own_status="PASS",interface_status="PASS",reason="ORDINARY_OWN_CHANGE")
            tr=ctx["before"]["trace"]; a=tr if actor=="A" else ctx["other_trace"]; h=tr if actor=="H" else ctx["other_trace"]
            out["feedback"]=relation(a,h,ctx["r"]); out["joint_trace"]=joint_trace(out["feedback"],"E1")
        else:
            try:
                evaluated=evaluate(f,e["selected_operation"],ctx["before"]["domain"])
                i=ctx["before"]["value"]; selected=next(r for r in evaluated["rows"] if r["input"]==i)
                out.update(own_status="PASS",interface_status=evaluated["s3_status"],composition=evaluated,
                           effective_trace=evaluated["effective_trace"],embedded_state=selected["embedded"],selected_operation=e["selected_operation"])
                out["after"]={"domain":f["states"],"value":selected["operated"],"law":f["law"],
                              "formation_trace":f["trace"],"effective_trace":evaluated["effective_trace"],"beta":f["beta"],"operations":f["operations"]}
                actual_beta=dict(zip(map(tuple,f["states"]),f["beta"]))[tuple(selected["operated"])]
                out["point_consistency"]={"actual_beta":actual_beta,"table_value":evaluated["effective_trace"][i],
                                          "equal":actual_beta==evaluated["effective_trace"][i]}
                log.add("SelectedOwnOperation",{"selector":e["selected_operation"],"before":i,"embedded":selected["embedded"],
                    "after":selected["operated"],"table_ref":digest(f["operations"][e["selected_operation"]])})
                log.add("EffectiveTrace",evaluated)
                if evaluated["s3_status"]!="PASS": out.update(status="PARTIAL",reason="S3_PROFILE_REJECTED")
                else:
                    tr=evaluated["effective_trace"]; a=tr if actor=="A" else ctx["other_trace"]; h=tr if actor=="H" else ctx["other_trace"]
                    out["feedback"]=relation(a,h,ctx["r"]); log.add("PsiFromEffectiveTrace",out["feedback"])
                    out["joint_trace"]=joint_trace(out["feedback"],ctx["policy"])
                    for row in out["joint_trace"]: log.add("JointOperation",row)
                    out.update(status="PASS",reason="ACTION_SPECIFIC_OWN_CHANGE")
            except (ValueError,KeyError,TypeError,IndexError) as exc: out.update(status="FAIL",reason=str(exc))
    log.add("Outcome",deepcopy(out)); out["journal"]=log.rows
    return out

def conjugation(g,p):
    inv=pointwise.inv_map(g)
    return [g[p[inv[x]]] for x in range(3)]

def pair(actor,ctx,x,y):
    cs=[x["feedback"]["c"],y["feedback"]["c"]]
    groups=[list(t) for t in permutations(range(3))]
    returns=[next(r["response"]["transition"]["after"]["x"] for r in z["joint_trace"] if r["request"]["op"]=="Return") for z in (x,y)]
    normalized=lambda e:{k:v for k,v in e.items() if k not in ("id","selected_operation")}
    return {"actor":actor,"same_context":x["context_ref"]==y["context_ref"]==digest(ctx),
            "events_only_selector_and_id_differ":normalized(x["event"])==normalized(y["event"]),
            "effective_traces":[x["effective_trace"],y["effective_trace"]],
            "different_effective_trace":x["effective_trace"]!=y["effective_trace"],
            "different_Psi_content":x["feedback"]!=y["feedback"],"c":cs,"anchored_returns":returns,
            "different_anchored_return":returns[0]!=returns[1],
            "same_capabilities":x["feedback"]["capabilities"]==y["feedback"]["capabilities"],"policy":"E1",
            "gauge":{"same_conjugacy_class":any(conjugation(g,cs[0])==cs[1] for g in groups),
                     "conjugators":[g for g in groups if conjugation(g,cs[0])==cs[1]],
                     "common_renaming_keeps_difference":all(conjugation(g,cs[0])!=conjugation(g,cs[1]) for g in groups),
                     "return_covariance":all(conjugation(g,c)[g[0]]==g[c[0]] for g in groups for c in cs),
                     "fixed_context_stabilizer":[g for g in groups if g[0]==0 and conjugation(g,ctx["other_trace"])==ctx["other_trace"]],
                     "new_gauge_invariant_class":False,"anchor":0,"orientation":"0→1→2→0"}}

def replay(g,c,f,choices):
    prefix,ctx=replay_context(g,c,f)
    results={n:execute_expected(ctx[v["actor"]],v["event"]) for n,v in choices.items()}
    pairs={}
    for actor,names in (("H",("H-T","H-A")),("A",("A-S","A-R"))):
        if all(n in results for n in names) and all(results[n]["status"]=="PASS" for n in names):
            pairs[actor]=pair(actor,ctx[actor],*(results[n] for n in names))
    identity={}
    for actor,context in ctx.items():
        f=context["formation"]; beta=dict(zip(map(tuple,f["states"]),f["beta"]))
        identity[actor]={"scope":"analytical identity after chi, NOT an actor event","event":None,
                         "trace":[beta[tuple(s)] for s in f["embedding"]]}
    return {"schema":"source-x-action-specific/0.3a","prefix":prefix,"contexts":ctx,"branches":results,"comparisons":pairs,
            "identity_controls":identity,"formal_novelty_against_E0plus":"FAIL","unresolved":LIMITS,
            "Seal_limit":"noninjective globally/reachable; injective on chi-image; actual variable-loss remains unproven"}

def verify(artifact,g,c,f,choices):
    import independent as diff
    try: problems=diff.differences(artifact,replay(g,c,f,choices))
    except (ValueError,KeyError,TypeError,IndexError) as e: problems=["malformed: "+str(e)]
    return {"status":"PASS" if not problems else "FAIL","problems":problems[:100],
            "scope":"conditional authored action-specific beta O chi / Psi causality","unresolved":LIMITS}

if __name__=="__main__":
    import argparse
    import sys
    p=argparse.ArgumentParser(); p.add_argument("--artifact",required=True); args=p.parse_args()
    g=load(V02/"fixtures/genesis.json"); c=load(V02/"fixtures/continuations.json"); f=load(V03/"fixtures/history_inputs.json")
    choices=load(ROOT/"fixtures/choices.json")["cases"]
    result=verify(load(args.artifact),g,c,f,choices)
    print(__import__("canonical").encode(result).decode(),end="")
    sys.exit(0 if result["status"]=="PASS" else 1)

