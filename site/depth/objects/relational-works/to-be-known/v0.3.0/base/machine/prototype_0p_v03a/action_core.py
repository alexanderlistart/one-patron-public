"""v0.3a actor-selected O; effective trace is beta O chi, never Formation.trace."""
from copy import deepcopy
from itertools import permutations
from location_a import digest
import feedback as historical
import core as old

SEM="operation-semantics/0.3a"
LIMITS=["r-origin","H-2","personal/numerical identity","Strong CO-EVOLVE","X4"]

def contexts(g,c,f):
    inputs={"schema":f["schema"],"histories":f["histories"]}
    prefix=historical.build(g,c,inputs,lambda _: {})
    h=prefix["histories"]["alpha"]; snap=prefix["snapshots"]["alpha"]
    result={}
    for actor in ("A","H"):
        result[actor]={"semantic_version":SEM,"actor":actor,"history_ref":digest(h),
                       "history_head":h["journal"][-1]["digest"],"W":prefix["witnesses"]["alpha"],
                       "formation":prefix["formations"]["alpha"][actor],"before":snap[actor],
                       "r":snap["interfaces"]["r"],"other_trace":snap["H" if actor=="A" else "A"]["trace"],
                       "policy":"E1","graph":snap["Psi"]["graph"],"anchor":0,"orientation":[[0,1],[1,2],[2,0]],
                       "covenant":h["covenant"],"old_E0_verdict":h["old_E0_verdict"]}
    return prefix,result

def evaluate_full(f,selector,domain):
    if f.get("status")!="PASS" or selector not in f.get("operations",{}):
        raise ValueError("OPERATION_NOT_IN_OWN_TYPE")
    states=f["states"]; beta=f["beta"]; chi=f["embedding"]; table=f["operations"][selector]
    if (domain!=[0,1,2] or len(states)!=len({tuple(s) for s in states}) or
        len(beta)!=len(states) or len(table)!=len(states) or len(chi)!=len(domain) or
        any(type(x) is not int or x not in domain for x in beta) or
        any(s not in states for s in chi) or any(s not in states for s in table)):
        raise ValueError("PARTIAL_OR_ILL_TYPED_FUNCTION")
    rows=[]
    for i in domain:
        embedded=deepcopy(chi[i])
        operated=deepcopy(table[states.index(embedded)])
        projected=beta[states.index(operated)]
        rows.append({"input":i,"embedded":embedded,"operated":operated,"projected":projected})
    effective=[r["projected"] for r in rows]
    return {"rows":rows,"effective_trace":effective,
            "s3_status":"PASS" if old.perm(effective) else "FAIL"}

def psi_content(a,h,r):
    p=old.make_psi(a,h,r,{})
    return {k:deepcopy(p[k]) for k in ("a","h","r","b","c","graph","transports","order","fixed")} | {
        "sections":[[x,x,x] for x in p["fixed"]],
        "capabilities":["GlobalJoin"] if p["fixed"] else ["Cyclic","Path","Reverse","Return"]}

class JointRuntime:
    def __init__(self,p,policy):
        if policy!="E1": raise ValueError("STALE_POLICY")
        self.p=p; self.scope=digest(p); self.issued=set()
    def _token(self,m):
        t={"policy":"E1","scope":self.scope,"state":m.state(),"x0":m.x0}
        self.issued.add(digest(t)); return t
    def _machine(self,k=0,x0=0):
        return old.Cyclic({"graph":self.p["graph"],"transports":self.p["transports"],"c":self.p["c"],
                           "order":self.p["order"],"fixed":self.p["fixed"],"transport_status":"PASS"},"E1",x0=x0,k=k)
    def form(self):
        m=self._machine()
        return {"request":{"op":"FormCyclic","policy":"E1","scope":self.scope},
                "response":{"status":"PASS","token":self._token(m)}}
    def execute(self,op,token,path=None):
        if token.get("scope")!=self.scope or token.get("policy")!="E1": raise ValueError("STALE_SCOPE")
        if digest(token) not in self.issued: raise ValueError("UNISSUED_STATE")
        m=self._machine(token["state"]["k"],token["x0"])
        if m.state()!=token["state"]: raise ValueError("STATE_INVARIANT")
        req={"op":op,"token":deepcopy(token),"path":deepcopy(path)}
        if op=="Return": step=m.returning()
        elif op=="Path": step=m.path(path)
        elif op=="Reverse": step=m.path(m.reverse(path))
        else: raise ValueError("OPERATION")
        return {"request":req,"response":{"status":"PASS","transition":step,"token":self._token(m)}}

def joint_execution(p,policy):
    if p["fixed"]:
        return [{"request":{"op":"GlobalJoin","policy":policy,"scope":digest(p)},
                 "response":{"status":"PASS","section":p["sections"][0]}}]
    rt=JointRuntime(p,policy); rows=[rt.form()]
    token=rows[-1]["response"]["token"]
    rows.append(rt.execute("Path",token,[[0,1]])); token=rows[-1]["response"]["token"]
    rows.append(rt.execute("Reverse",token,[[0,1]])); token=rows[-1]["response"]["token"]
    for _ in range(3):
        rows.append(rt.execute("Return",token)); token=rows[-1]["response"]["token"]
    return rows

def execute_choice(context,event):
    actor=context["actor"]; f=context["formation"]
    ledger=old.Journal("selected-own/"+actor,context["history_head"])
    ledger.append("Context",context,"E1"); ledger.append("Formation",f,"E1")
    result={"semantic_version":SEM,"context_ref":digest(context),"event":None,"status":"NOT ENACTED",
            "own_status":"NOT ENACTED","interface_status":"NOT EVALUATED","before":deepcopy(context["before"]),
            "after":deepcopy(context["before"]),"formation_trace":deepcopy(f.get("trace")),
            "effective_trace":None,"composition":None,"feedback":None,"joint_trace":[],
            "covenant_ref":"C0","eta_acceptance_ref":"C0","policy":"E1","unresolved":LIMITS}
    if event is not None:
        e=deepcopy(event); result["event"]=e; ledger.append("AuthoredChoice",e,"E1")
        keys={"id","kind","actor","source","origin","context","formation","action","selected_operation"}
        valid=(set(e)==keys and type(e["id"]) is str and bool(e["id"]) and e["id"] not in ("A0","A1","H0","C0","R0","h1") and
               e["kind"]=="OwnEnactment03a" and e["actor"]==actor and e["source"]==actor and
               e["context"]=="alpha:own:"+actor and e["formation"]=="alpha:formation:"+actor and
               e["action"] in ("relational","Ordinary","Pause"))
        if not valid: result.update(status="FAIL",reason="OWN_SOURCE_OR_SCHEMA")
        elif e["origin"]!="AUTHORED PREMISE": result.update(status="UNRESOLVED",reason="OWN_ORIGIN")
        elif e["action"]!="relational" and e["selected_operation"] is not None:
            result.update(status="FAIL",reason="SELECTOR_NOT_APPLICABLE")
        elif e["action"]=="Pause": result.update(status="PASS",reason="PAUSE")
        elif e["action"]=="Ordinary":
            result["after"]["value"]=context["before"]["trace"][context["before"]["value"]]
            result.update(status="PASS",own_status="PASS",interface_status="PASS",reason="ORDINARY_OWN_CHANGE")
            trace=context["before"]["trace"]
            a=trace if actor=="A" else context["other_trace"]
            h=trace if actor=="H" else context["other_trace"]
            result["feedback"]=psi_content(a,h,context["r"])
            result["joint_trace"]=joint_execution(result["feedback"],"E1")
        else:
            try:
                evaluated=evaluate_full(f,e["selected_operation"],context["before"]["domain"])
                point=context["before"]["value"]; row=evaluated["rows"][point]
                result.update(own_status="PASS",interface_status=evaluated["s3_status"],
                              composition=evaluated,effective_trace=evaluated["effective_trace"],
                              embedded_state=row["embedded"],selected_operation=e["selected_operation"])
                result["after"]={"domain":f["states"],"value":row["operated"],"law":f["law"],
                                 "formation_trace":f["trace"],"effective_trace":evaluated["effective_trace"],
                                 "beta":f["beta"],"operations":f["operations"]}
                actual_beta=f["beta"][f["states"].index(row["operated"])]
                result["point_consistency"]={"actual_beta":actual_beta,"table_value":evaluated["effective_trace"][point],
                                             "equal":actual_beta==evaluated["effective_trace"][point]}
                ledger.append("SelectedOwnOperation",{"selector":e["selected_operation"],"before":point,
                    "embedded":row["embedded"],"after":row["operated"],"table_ref":digest(f["operations"][e["selected_operation"]])},"E1")
                ledger.append("EffectiveTrace",evaluated,"E1")
                if evaluated["s3_status"]!="PASS":
                    result.update(status="PARTIAL",reason="S3_PROFILE_REJECTED")
                else:
                    trace=evaluated["effective_trace"]
                    a=trace if actor=="A" else context["other_trace"]
                    h=trace if actor=="H" else context["other_trace"]
                    result["feedback"]=psi_content(a,h,context["r"])
                    ledger.append("PsiFromEffectiveTrace",result["feedback"],"E1")
                    result["joint_trace"]=joint_execution(result["feedback"],context["policy"])
                    for step in result["joint_trace"]: ledger.append("JointOperation",step,"E1")
                    result.update(status="PASS",reason="ACTION_SPECIFIC_OWN_CHANGE")
            except (ValueError,KeyError,TypeError,IndexError) as exc:
                result.update(status="FAIL",reason=str(exc))
    ledger.append("Outcome",deepcopy(result),"E1"); result["journal"]=ledger.entries
    return result

def first_return(result):
    return next(s["response"]["transition"]["after"]["x"] for s in result["joint_trace"] if s["request"]["op"]=="Return")

def conjugate(g,p): return old.compose(g,old.compose(p,old.inverse(g)))

def compare_pair(actor,context,x,y):
    c1,c2=x["feedback"]["c"],y["feedback"]["c"]
    gs=[list(g) for g in permutations(range(3))]
    normalized=lambda e:{k:v for k,v in e.items() if k not in ("id","selected_operation")}
    return {"actor":actor,"same_context":x["context_ref"]==y["context_ref"]==digest(context),
            "events_only_selector_and_id_differ":normalized(x["event"])==normalized(y["event"]),
            "effective_traces":[x["effective_trace"],y["effective_trace"]],
            "different_effective_trace":x["effective_trace"]!=y["effective_trace"],
            "different_Psi_content":x["feedback"]!=y["feedback"],"c":[c1,c2],
            "anchored_returns":[first_return(x),first_return(y)],
            "different_anchored_return":first_return(x)!=first_return(y),
            "same_capabilities":x["feedback"]["capabilities"]==y["feedback"]["capabilities"],"policy":"E1",
            "gauge":{"same_conjugacy_class":any(conjugate(g,c1)==c2 for g in gs),
                     "conjugators":[g for g in gs if conjugate(g,c1)==c2],
                     "common_renaming_keeps_difference":all(conjugate(g,c1)!=conjugate(g,c2) for g in gs),
                     "return_covariance":all(conjugate(g,c)[g[0]]==g[c[0]] for g in gs for c in (c1,c2)),
                     "fixed_context_stabilizer":[g for g in gs if g[0]==0 and conjugate(g,context["other_trace"])==context["other_trace"]],
                     "new_gauge_invariant_class":False,"anchor":0,"orientation":"0→1→2→0"}}

def build(g,c,f,choice_loader):
    prefix,ctx=contexts(g,c,f)
    choices=choice_loader(deepcopy(ctx))
    results={name:execute_choice(ctx[v["actor"]],v["event"]) for name,v in choices.items()}
    pairs={}
    for actor,names in (("H",("H-T","H-A")),("A",("A-S","A-R"))):
        if all(name in results for name in names) and all(results[name]["status"]=="PASS" for name in names):
            pairs[actor]=compare_pair(actor,ctx[actor],*(results[name] for name in names))
    controls={}
    for actor,context in ctx.items():
        definition=context["formation"]
        controls[actor]={"scope":"analytical identity after chi, NOT an actor event",
                         "event":None,"trace":[definition["beta"][definition["states"].index(s)] for s in definition["embedding"]]}
    return {"schema":"source-x-action-specific/0.3a","prefix":prefix,"contexts":ctx,"branches":results,
            "comparisons":pairs,"identity_controls":controls,"formal_novelty_against_E0plus":"FAIL","unresolved":LIMITS,
            "Seal_limit":"noninjective globally/reachable; injective on chi-image; actual variable-loss remains unproven"}

