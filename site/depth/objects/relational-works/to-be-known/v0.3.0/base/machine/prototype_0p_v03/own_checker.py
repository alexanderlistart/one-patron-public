"""Independent new-property verification. No feedback.py/continuing.py/core.py imports."""
from copy import deepcopy
from itertools import product
from location import V01, load, digest
import verifier as initial
import independent as previous

I=[0,1,2]
TRI=[[0,1],[1,2],[2,0]]
LIMITS=["r-origin","H-2","personal/numerical identity","Strong CO-EVOLVE","X4"]

class Ledger:
    def __init__(self,branch,head): self.branch=branch; self.head=head; self.rows=[]
    def add(self,kind,payload):
        e={"seq":len(self.rows),"branch":self.branch,"previous":self.head,"kind":kind,"policy":"E1","payload":deepcopy(payload)}
        e["digest"]=digest(e); self.head=e["digest"]; self.rows.append(e)

def calc_psi(a,h,r,version):
    _,c,_,fixed=initial.algebra(a,h,r)
    return {"version":version,"a":a,"h":h,"r":r,"graph":TRI,"transports":[I,I,c],
            "c":c,"sections":[[x]*3 for x in fixed],
            "operations":["GlobalJoin"] if fixed else ["Cyclic","Path","Return"]}

def history(g,contexts,cfg,base):
    if not cfg.get("r_enabled"):
        missing=deepcopy(g); missing['events']=[e for e in missing['events'] if e['kind']!='RInterfaceEvent']
        derived=initial.derive(missing,'H1')
        local={'A_exists':'AHistory' in {e['kind'] for e in missing['events']},
               'H_exists':'HHistory' in {e['kind'] for e in missing['events']},
               'r_present':'RInterfaceEvent' in {e['kind'] for e in missing['events']},
               'policy':derived['active'],'joint':derived['cyclic']['status']}
        return {"status":"BLOCKED","reason":"NO_R","prefix":None,"journal":[],"current":None,
                "address_map":cfg["address_map"],'source_inputs':missing,'local_prefix':local}
    s=deepcopy(contexts["cases"][cfg["prefix"]])
    if cfg.get("bridge_phi_override"): s["bridge"]["phi"]=deepcopy(cfg["bridge_phi_override"])
    prefix=previous.replay(g,s,base)
    if prefix["psi2"] is None:
        return {"status":"BLOCKED","reason":"NO_ADMITTED_PREFIX","prefix":prefix,"journal":[],"current":None,"address_map":cfg["address_map"]}
    l=Ledger("own-history",prefix["journal"][-1]["digest"])
    l.add("PrefixExecuted",{"last_execution":digest(prefix["trace"]),"prefix_head":l.head})
    e=deepcopy(cfg.get("terminal"))
    if e:
        valid=(e.get("source"),e.get("kind"),e.get("origin"),e.get("parents"),e["payload"].get("covenant_ref"))==(
            "H","HTerminalOwnChange","AUTHORED PREMISE",["C0","prefix:executed"],"C0") and initial.check_bridge(e)
        l.add("TerminalHInput",e)
        if not valid: return {"status":"BLOCKED","reason":"TERMINAL_SOURCE_OR_BETA","prefix":prefix,"journal":l.rows,"current":None,"address_map":cfg["address_map"]}
        h=e["payload"]["trace"]
    else: h=prefix["psi2"]["h"]
    p=calc_psi(prefix["psi2"]["a"],h,prefix["psi2"]["r"],"Psi/current")
    a_input=next(e for e in g['events'] if e['id']=='A1')['payload']
    a_state=dict((tuple(x),y) for x,y in zip(a_input['before'],a_input['map']))[(0,0)]
    h_input=g['branches']['H1']['event']['payload']
    h_state=dict((tuple(x),y) for x,y in zip(h_input['before'],h_input['map']))[(0,0)]
    for own in [prefix['candidate']]+([e] if e else []):
        payload=own['payload']; table=dict((tuple(x),y) for x,y in zip(payload['before'],payload['map']))
        h_state=table[(0,h_state)]
    own_current={'A':{'domain':I,'value':a_state,'trace':p['a'],'law':'A/local/1'},
                 'H':{'domain':I,'value':h_state,'trace':p['h'],'law':'H/local/1'}}
    l.add("CurrentPsi",p)
    l.add("InheritedFormation",{"GlobalJoin":"PASS" if p["sections"] else "FAIL","Cyclic":"BLOCKED" if p["sections"] else "PASS"})
    return {"status":"PASS","prefix":prefix,"prefix_input":s,"terminal":e,"current":p,"own_current":own_current,"address_map":cfg["address_map"],
            "journal":l.rows,"old_E0_verdict":prefix["old_E0_verdict"],"covenant":prefix["covenant"],"policy":"E1"}

def observe(h):
    if h["status"]!="PASS": return None
    p=h["current"]
    return {"A":deepcopy(h['own_current']['A']),
            "H":deepcopy(h['own_current']['H']),
            "policy":"E1","interfaces":{"I_A":I,"I_H":I,"r":p["r"]},
            "Psi":{k:deepcopy(p[k]) for k in ("graph","transports","c","sections","operations")},
            "ordinary_own":{"A":["OrdinaryTrace","Pause"],"H":["OrdinaryTrace","Pause"]}}

def certificate(h,g):
    if h["status"]!="PASS": return {"status":"BLOCKED","reason":h.get("reason","NO_HISTORY")}
    p=h["prefix"]
    if p["admission"]["status"]!="PASS": return {"status":"BLOCKED","reason":"UNATTRIBUTED_HISTORY"}
    squares=previous.judge_bridge(p["psi1"],p["psi2"],p["proposal"],p["candidate"],True)
    if squares["strict"]!="PRESERVED":
        return {"status":"BLOCKED","reason":"NO_PRESERVED_HISTORICAL_TRANSPORT","bridge":squares}
    if p["transfer"]["status"]!="PASS" or not p["trace"] or p["trace"][-1]["response"]["status"]!="PASS":
        return {"status":"BLOCKED","reason":"NO_EXECUTED_TRANSFER_RETURN"}
    _,bad,uncertain=initial.event_check(g["events"]+[g["branches"]["H1"]["event"]])
    if bad or uncertain: return {"status":"UNRESOLVED","reason":"H_A_R_SOURCE"}
    if h["address_map"]!=I or h["current"]["r"]!=p["psi2"]["r"]:
        return {"status":"BLOCKED","reason":"NO_CURRENT_ADDRESS_BRIDGE"}
    path=p["trace"][-1]["response"]["transition"]["path"]
    if path!=TRI: return {"status":"BLOCKED","reason":"HISTORICAL_CYCLE_DOMAIN"}
    loop=[previous.transport(p["psi1"],path,x) for x in I]
    ph=p["proposal"]["phi"][0]
    frame=[]; at=0
    for n in range(3):
        frame.append(ph[at]); at=loop[at]
    if set(frame)!=set(I) or at!=0: return {"status":"FAIL","reason":"NON_ORBIT"}
    succ=[frame[(frame.index(x)+1)%3] for x in I]
    if p["transfer"]["token"]["state"]["x"]!=frame[1] or p["trace"][-1]["response"]["transition"]["after"]["x"]!=frame[2]:
        return {"status":"FAIL","reason":"ORBIT_NOT_EXECUTED"}
    return {"status":"PASS","scope":"historical orbit, NOT current monodromy","path":path,"frame":frame,
            "successor":succ,"squares":squares["squares"],"transfer":digest(p["transfer"]),
            "execution":digest(p["trace"][-1]),"preserved_source":p["candidate"]["id"],
            "address_map":h["address_map"],"current_c":h["current"]["c"],
            "origin":"AUTHORED PREMISE / STRUCTURALLY VERIFIED"}

def formation(actor,w,snap):
    if w["status"]!="PASS" or snap is None:
        return {"status":"BLOCKED","reason":"HISTORICAL_WITNESS_REQUIRED","ordinary":["OrdinaryTrace","Pause"]}
    if actor=="H":
        r=snap["interfaces"]["r"]; back=initial.inv_map(r)
        trace=[back[w["successor"][r[i]]] for i in I]
    else:
        a=snap["A"]["trace"]; back=initial.inv_map(a)
        trace=[a[w["successor"][back[i]]] for i in I]
    states=[[i,z] for i in I for z in range(3 if actor=="H" else 2)]
    embed=[[trace[i],int(actor=="A")] for i in I]
    ops={}
    if actor=="H":
        ops["Turn"]=[[i,(z+1)%3] for i,z in states]
        ops["Advance"]=[[trace[i],z] for i,z in states]
    else:
        ops["Seal"]=[[i,0] for i,z in states]
        ops["Readdress"]=[[trace[i],z] for i,z in states]
    return {"status":"PASS","actor":actor,"type":"HOrbitRefinement" if actor=="H" else "AAddressSeal",
            "scope":"own local object sort; not E2","witness":digest(w),"states":states,
            "beta":[row[0] for row in states],"embedding":embed,"trace":trace,"operations":ops,
            "law":actor+"/relational-local/2","ordinary":["OrdinaryTrace","Pause"],"new_beta_fibre_size":3 if actor=="H" else 2}

def enact_expected(h,f,actor,e):
    snap=observe(h)
    if snap is None: return {"status":"BLOCKED","reason":"NO_CURRENT_CONTEXT","event":deepcopy(e)}
    before=deepcopy(snap[actor]); l=Ledger("own-enactment/"+actor,h["journal"][-1]["digest"]); l.add("Formation",f)
    out={"status":"NOT ENACTED","event":None,"before":before,"after":deepcopy(before),"feedback":None,
         "operation_trace":[],"covenant_ref":"C0","eta_acceptance_ref":"C0","policy":"E1","unresolved":LIMITS}
    if e is not None:
        e=deepcopy(e); out["event"]=e; l.add("AuthoredOwnInput",e)
        expectedkeys={"id","kind","actor","source","origin","context","formation","action"}
        valid=(set(e)==expectedkeys and isinstance(e["id"],str) and bool(e["id"]) and e["id"] not in {"A0","A1","H0","h1","C0","R0"}
               and (e["kind"],e["actor"],e["source"],e["context"],e["formation"])==(
                   "OwnEnactment",actor,actor,"own:current:"+actor,"own:formation:"+actor)
               and e["action"] in {"relational","ordinary","Pause"})
        if not valid: out.update(status="FAIL",reason="OWN_SOURCE_OR_SCHEMA")
        elif e["origin"]!="AUTHORED PREMISE": out.update(status="UNRESOLVED",reason="OWN_ORIGIN")
        elif e["action"]=="Pause": out.update(status="PASS",reason="PAUSE")
        elif e["action"]=="relational" and f["status"]!="PASS": out.update(status="BLOCKED",reason="TYPE_NOT_FORMED")
        else:
            if e["action"]=="relational":
                value=f["embedding"][before["value"]]
                out["after"]={"domain":f["states"],"value":value,"trace":f["trace"],"law":f["law"],
                              "beta":f["beta"],"operations":f["operations"]}
                out['embedding_value']=deepcopy(value)
                out["beta_equation"]=[row[0]==f["trace"][i] for i,row in enumerate(f["embedding"])]
                for name in (['Turn'] if actor=='H' else ['Seal']):
                    table=f['operations'][name]
                    value2=table[next(i for i,row in enumerate(f["states"]) if row==value)]
                    out["operation_trace"].append({"operation":name,"before":value,"after":value2}); value=value2
                out['after']['value']=deepcopy(value)
                out["local_install"]={"actor":actor,"from":before["law"],"to":f["law"],"formation":digest(f),"event":e["id"]}
            else: out["after"]["value"]=before["trace"][before["value"]]
            a=out["after"]["trace"] if actor=="A" else snap["A"]["trace"]
            hh=out["after"]["trace"] if actor=="H" else snap["H"]["trace"]
            p=calc_psi(a,hh,snap["interfaces"]["r"],"Psi/feedback/"+actor); out["feedback"]=p
            if not p["sections"]:
                # Direct edge transport, no core k executor.
                x=0
                for edge,t in zip(TRI,p["transports"]): x=t[x]
                step={"path":TRI,"before":{"k":0,"q":0,"vertex":0,"x":0},
                      "after":{"k":3,"q":1,"vertex":0,"x":x}}
                out["joint_execution"]={"status":"PASS","operation":"Return","trace":step}
            else: out["joint_execution"]={"status":"PASS","operation":"GlobalJoin","section":p["sections"][0]}
            out.update(status="PASS",reason="SELF_ENACTED_OWN_CHANGE")
    l.add("OwnOutcome",deepcopy(out)); out["journal"]=l.rows
    return out

def replay(g,contexts,inputs,choices):
    base=load(V01/"evidence/final1/core_evidence.json")
    if initial.verify(base,g)["status"]!="PASS": raise ValueError("old prefix invalid")
    hs={n:history(g,contexts,cfg,base) for n,cfg in inputs["histories"].items()}
    ss={n:observe(h) for n,h in hs.items()}
    ws={n:certificate(h,g) for n,h in hs.items()}
    fs={n:{a:formation(a,ws[n],ss[n]) for a in ("A","H")} for n in hs}
    es={n:enact_expected(hs[c["history"]],fs[c["history"]][c["actor"]],c["actor"],c["event"]) for n,c in choices.items()}
    return {"schema":"source-x-own-feedback/3","histories":hs,"snapshots":ss,"witnesses":ws,"formations":fs,"enactments":es,
            "snapshot_equal":ss["alpha"]==ss["beta"],"history_equal":digest(hs["alpha"])==digest(hs["beta"]),
            "formal_novelty_against_E0plus":"FAIL","unresolved":LIMITS}

def verify(a,g,contexts,inputs,choices):
    try:
        expected=replay(g,contexts,inputs,choices)
        errors=previous.differences(a,expected)
    except (KeyError,ValueError,TypeError,IndexError) as e: errors=["malformed: "+str(e)]
    return {"status":"PASS" if not errors else "FAIL","problems":errors[:100],
            "scope":"conditional own formation/enactment; finite structural replay, not external ontology",
            "unresolved":LIMITS}

if __name__=='__main__':
    import argparse
    import sys
    from location import ROOT,V02,load,encode
    p=argparse.ArgumentParser(); p.add_argument('--artifact',required=True); args=p.parse_args()
    g=load(V02/'fixtures/genesis.json'); c=load(V02/'fixtures/continuations.json'); f=load(ROOT/'fixtures/history_inputs.json')
    result=verify(load(args.artifact),g,c,f,f['choices'])
    print(encode(result).decode(),end='')
    sys.exit(0 if result['status']=='PASS' else 1)

