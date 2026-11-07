"""Continuing authored history. Future events are admitted only by an explicit call."""
from copy import deepcopy
from itertools import product
from environment import digest
import core as old

TRI = [[0,1],[1,2],[2,0]]
CTX = "H1:E1:operations-completed"

def edge_map(psi, edge):
    for e,t in zip(psi["graph"],psi["transports"]):
        if e == edge:
            return t
        if e == list(reversed(edge)):
            return old.inverse(t)
    raise ValueError("EDGE_NOT_IN_SCOPE")

def along(psi, path):
    value=[0,1,2]
    for edge in path:
        value=old.compose(edge_map(psi,edge),value)
    return value

def new_psi(a, service, r):
    raw=old.make_psi(a["payload"]["trace"],service["payload"]["trace"],r["payload"]["map"],
                     {"a":a["id"],"h":service["id"],"r":r["id"]})
    graph=service["payload"].get("structure",{}).get("to",TRI)
    if graph not in (TRI,TRI[:2]):
        raise ValueError("FACTOR_PROFILE")
    ts=[raw["transports"][TRI.index(e)] for e in graph]
    result={"version":"Psi/2","parent":"Psi/1","graph":graph,"transports":ts,
            "a":raw["a"],"h":raw["h"],"r":raw["r"],"b":raw["b"],"trace_commutator":raw["c"],
            "refs":raw["refs"],"Lost":service["payload"]["Lost"]}
    result["monodromy"]=along(result,TRI) if all(e in graph for e in TRI) else None
    result["sections"]=[list(row) for row in product(range(3),repeat=3)
                        if all(t[row[u]]==row[v] for (u,v),t in zip(graph,ts))]
    result["cyclic"]=bool(result["monodromy"] is not None and
                           old.order(result["monodromy"])==3 and
                           not any(result["monodromy"][i]==i for i in range(3)))
    return result

def bridge_check(p1,p2,proposal,event,licensed):
    absent={"strict":"INSUFFICIENT EVIDENCE","historical":"INSUFFICIENT EVIDENCE","squares":[]}
    if not licensed or proposal is None:
        return absent
    if (proposal.get("from")!="Psi/1" or proposal.get("to")!="Psi/2" or
            proposal.get("source_event_ref")!=event["id"] or
            not old.perm(proposal.get("vertices")) or
            not isinstance(proposal.get("phi"),list) or len(proposal["phi"])!=3 or
            not all(old.perm(p) for p in proposal["phi"])):
        return {"strict":"OBSTRUCTED","historical":"INSUFFICIENT EVIDENCE","squares":[]}
    squares=[]
    for (u,v),t in zip(p1["graph"],p1["transports"]):
        path=proposal.get("paths",{}).get(str(u)+"-"+str(v))
        if path is None:
            return {"strict":"NOT TRANSPORTABLE","historical":"NOT TRANSPORTABLE","squares":squares}
        at=proposal["vertices"][u]
        for edge in path:
            if edge[0]!=at:
                return {"strict":"OBSTRUCTED","historical":"OBSTRUCTED","squares":squares}
            at=edge[1]
        if at!=proposal["vertices"][v]:
            return {"strict":"OBSTRUCTED","historical":"OBSTRUCTED","squares":squares}
        try:
            target=along(p2,path)
        except ValueError:
            return {"strict":"NOT TRANSPORTABLE","historical":"NOT TRANSPORTABLE","squares":squares}
        left=old.compose(proposal["phi"][v],t)
        right=old.compose(target,proposal["phi"][u])
        squares.append({"edge":[u,v],"path":path,"left":left,"right":right,"commutes":left==right})
    same=all(s["commutes"] for s in squares)
    licensed_change=(proposal.get('allow_transport_change') and p1['graph']==p2['graph'] and
                      proposal['vertices']==[0,1,2] and proposal['phi']==[[0,1,2]]*3 and
                      proposal['paths']=={'0-1':[[0,1]],'1-2':[[1,2]],'2-0':[[2,0]]} and
                      p1['transports']!=p2['transports'])
    return {"strict":"PRESERVED" if same else "OBSTRUCTED",
            "historical":"PRESERVED" if same else "TRANSFORMED" if licensed_change else "OBSTRUCTED",
            "squares":squares}

def profile(p):
    if p.get("version")=="Psi/1":
        return p
    if not p["cyclic"]:
        raise ValueError("CYCLIC_NOT_APPLICABLE")
    return {"graph":p["graph"],"transports":p["transports"],"c":p["monodromy"],
            "order":old.order(p["monodromy"]),"fixed":[],
            "transport_status":"PASS"}

class Session:
    def __init__(self, genesis):
        # This phase knows no continuation fixture or candidate id.
        self.genesis=deepcopy(genesis)
        self.base=old.execute(self.genesis)
        b=self.base["branches"]["H1"]
        if b["active_policy"]!="E1" or len(b["operations"])!=5:
            raise ValueError("EXECUTED_E1_REQUIRED")
        self.p1=deepcopy(b["psi"])
        self.p2=None
        self.current="Psi/1"
        self.policy="E1"
        self.h_ids=["H0","C0","h1"]
        self.ids=[e["id"] for e in genesis["events"]]+["h1",CTX]
        self.log=old.Journal("H1/continuing",b["journal"][-1]["digest"])
        self.context={"id":CTX,"install_ref":next(e["digest"] for e in b["journal"] if e["kind"]=="Install"),
                      "execution_ref":next(e["digest"] for e in reversed(b["journal"]) if e["kind"]=="Reverse"),
                      "psi1_digest":digest(self.p1),"old_verdict_digest":digest(b["global"]),
                      "policy":"E1","active_ids":deepcopy(self.ids),"H_history":deepcopy(self.h_ids)}
        self.log.append("ContinuationContext",self.context,"E1")
        self.before=deepcopy({"context":self.context,"journal":self.log.entries})
        self.trace=[]
        self.issued=set()
        self.admission=None
        self.bridge=None
        self.candidate=None
        self.request("Cyclic","Psi/1",policy="E1")
        token=self.trace[-1]["response"].get("token")
        self.request("Return","Psi/1",token=token)
        self.pre_token=deepcopy(self.trace[-1]["response"]["token"])

    def admit(self, candidate, proposal):
        if self.candidate is not None:
            raise ValueError("ONLY_ONE_NEW_ACT_PER_TRIAL")
        self.candidate=deepcopy(candidate)
        self.proposal=deepcopy(proposal)
        self.log.append("RecordedCandidate",self.candidate,"E1")
        e=self.candidate
        valid_kind=e.get("kind") in ("HServiceAfterE1","HStructuralChangeAfterE1","HRevisionOrPause")
        source=(e.get("source")=="H" and valid_kind)
        parents=e.get("parents",[])
        linked=(isinstance(parents,list) and CTX in parents and "h1" in parents and "C0" in parents and
                all(p in self.ids for p in parents) and e.get("id") not in self.ids and
                e.get("payload",{}).get("covenant_ref")=="C0")
        origin=e.get("origin")=="AUTHORED PREMISE"
        pause=e.get("kind")=="HRevisionOrPause"
        math=True if pause else old.bridge(e)
        structure=e.get("payload",{}).get("structure")
        struct_ok=(not structure or
                   (e["kind"]=="HStructuralChangeAfterE1" and structure.get("from")==TRI and
                    structure.get("to")==TRI[:2] and bool(structure.get("reason"))))
        if e.get("kind")=="HStructuralChangeAfterE1" and not structure:
            struct_ok=False
        status="FAIL" if not source or not linked or not math or not struct_ok else "UNRESOLVED" if not origin else "PASS"
        self.admission={"status":status,"origin":"AUTHORED PREMISE" if origin else "UNRESOLVED",
                        "source":"STRUCTURALLY VERIFIED" if source and linked else "FAIL",
                        "covenant_ref":"C0","eta_acceptance_ref":"C0",
                        "reason":"H_PAUSE" if status=="PASS" and pause else "H_OWNED_AFTER_EXECUTED_E1" if status=="PASS" else "SOURCE_OR_CONTEXT"}
        self.log.append("Admission",self.admission,"E1")
        a=next(x for x in self.genesis["events"] if x["id"]=="A1")
        r=next(x for x in self.genesis["events"] if x["id"]=="R0")
        self.math_candidate=new_psi(a,e,r) if not pause and math and struct_ok else None
        if status=="PASS":
            self.ids.append(e["id"]); self.h_ids.append(e["id"])
            if not pause:
                self.p2=deepcopy(self.math_candidate)
                self.current="Psi/2"
                self.log.append("PsiVersion2",self.p2,"E1")
        self.bridge=bridge_check(self.p1,self.p2,proposal,e,self.p2 is not None) if self.p2 else {
            "strict":"INSUFFICIENT EVIDENCE","historical":"INSUFFICIENT EVIDENCE","squares":[]}
        self.log.append("BridgeJudgements",self.bridge,"E1")
        return deepcopy(self.admission)

    def _token(self, psi, k=0, x0=0):
        p=self.p1 if psi=="Psi/1" else self.p2
        machine=old.Cyclic(profile(p),"E1",x0=x0,k=k)
        token={"psi":psi,"psi_digest":digest(p),"policy":"E1","state":machine.state(),"x0":x0}
        self.issued.add(digest(token))
        return token

    def request(self, op, psi, mode="current", token=None, policy="E1"):
        query={"op":op,"psi":psi,"mode":mode,"policy":policy,"token":deepcopy(token)}
        p=self.p1 if psi=="Psi/1" else self.p2 if psi=="Psi/2" else None
        if policy!=self.policy:
            ans={"status":"FAIL","reason":"STALE_POLICY"}
        elif p is None:
            ans={"status":"BLOCKED","reason":"NO_PSI"}
        elif mode not in ("current","historical"):
            ans={"status":"FAIL","reason":"MODE"}
        elif mode=="current" and psi!=self.current:
            ans={"status":"FAIL","reason":"STALE_PSI"}
        elif token and (token.get("psi")!=psi or token.get("psi_digest")!=digest(p) or token.get("policy")!=policy):
            ans={"status":"FAIL","reason":"STALE_STATE_SCOPE"}
        elif token and digest(token) not in self.issued:
            ans={"status":"FAIL","reason":"UNISSUED_STATE"}
        else:
            cyclic=bool(p.get("cyclic")) if psi=="Psi/2" else p["order"]==3 and not p["fixed"]
            licensed=(psi=="Psi/1" or self.admission and self.admission["status"]=="PASS")
            if op=="GlobalJoin":
                sections=p["sections"] if psi=="Psi/2" else [[x,x,x] for x in p["fixed"]]
                ans={"status":"PASS" if licensed and sections else "FAIL",
                     "reason":"GLOBAL_SECTION" if sections else "GLOBAL_SECTION_OBSTRUCTED","sections":sections,
                     "policy":"E1","psi":psi}
            elif op=="Cyclic":
                ans={"status":"PASS","token":self._token(psi)} if licensed and cyclic else {"status":"BLOCKED","reason":"CYCLIC_NOT_APPLICABLE"}
            elif op=="Return":
                if not cyclic:
                    ans={"status":"BLOCKED","reason":"CYCLIC_NOT_APPLICABLE"}
                elif not token:
                    ans={"status":"FAIL","reason":"STATE_REQUIRED"}
                else:
                    try:
                        machine=old.Cyclic(profile(p),"E1",x0=token["x0"],k=token["state"]["k"])
                        if machine.state()!=token["state"]:
                            raise ValueError("STATE_INVARIANT")
                        transition=machine.returning()
                        ans={"status":"PASS","transition":transition,
                             "token":self._token(psi,machine.k,token["x0"])}
                    except (ValueError,KeyError,TypeError):
                        ans={"status":"FAIL","reason":"STATE_INVARIANT"}
            else:
                ans={"status":"FAIL","reason":"UNKNOWN_OPERATION"}
        row={"request":query,"response":ans}
        self.trace.append(deepcopy(row))
        self.log.append("Operation",row,"E1")
        return deepcopy(ans)

    def transfer(self, token):
        # Only this explicitly checked identity path/fibre map has a lift-state transport rule.
        proposal=self.proposal
        good=(self.p2 and self.bridge["strict"]=="PRESERVED" and proposal["vertices"]==[0,1,2] and
              proposal["phi"]==[[0,1,2]]*3 and proposal["paths"]=={"0-1":[[0,1]],"1-2":[[1,2]],"2-0":[[2,0]]}
              and token==self.pre_token)
        answer={"status":"PASS","token":self._token("Psi/2",token["state"]["k"],token["x0"])} if good else {
            "status":"OBSTRUCTED" if self.bridge["strict"]=="OBSTRUCTED" else "NOT TRANSPORTABLE" if self.bridge["strict"]=="NOT TRANSPORTABLE" else "INSUFFICIENT EVIDENCE"}
        self.log.append("ExplicitStateTransfer",{"input":token,"result":answer},"E1")
        self.transfer_result=answer
        return deepcopy(answer)

    def finish(self):
        self.request("GlobalJoin","Psi/2")
        self.request("Cyclic","Psi/2")
        self.request("Return","Psi/2")
        self.request("Return","Psi/2",token=self.pre_token)
        self.request("Return","Psi/1",mode="historical",token=self.pre_token)
        self.request("Return","Psi/1",mode="current",token=self.pre_token)
        self.request("GlobalJoin",self.current,policy="E0")
        transferred=self.transfer(self.pre_token)
        if transferred["status"]=="PASS":
            self.request("Return","Psi/2",token=transferred["token"])
        return {"schema":"source-x-continuing/2","before":self.before,"context":self.context,
                "candidate":self.candidate,"admission":self.admission,"math_candidate":self.math_candidate,
                "active_ids":self.ids,"H_history":self.h_ids,"psi1":self.p1,"psi2":self.p2,"current":self.current,
                "policy":self.policy,"old_E0_verdict":deepcopy(self.base["branches"]["H1"]["global"]),
                "covenant":deepcopy(next(e for e in self.genesis["events"] if e["id"]=="C0")),
                "bridge":self.bridge,"proposal":self.proposal,"trace":self.trace,
                "transfer":self.transfer_result,"journal":self.log.entries,
                "formal_novelty_against_E0plus":"FAIL",
                "unresolved":["r-origin","H-2","personal/numerical identity","Strong CO-EVOLVE","X4"]}

def execute_scenario(genesis, scenario):
    runtime=Session(genesis)
    runtime.admit(scenario["event"],scenario.get("bridge"))
    return runtime.finish()

