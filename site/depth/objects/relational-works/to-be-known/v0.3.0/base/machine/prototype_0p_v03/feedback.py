"""Finite history-dependent own transformations; authored choices are never generated."""
from copy import deepcopy
from itertools import product
from location import digest
import core as one
import continuing as two

IDENT=[0,1,2]
TRI=[[0,1],[1,2],[2,0]]
LIMITS=["r-origin","H-2","personal/numerical identity","Strong CO-EVOLVE","X4"]

def psi(a,h,r,version):
    p=one.make_psi(a,h,r,{"a":"current-A","h":"current-H","r":"R0"})
    return {"version":version,"a":a,"h":h,"r":r,"graph":p["graph"],"transports":p["transports"],
            "c":p["c"],"sections":[[x,x,x] for x in p["fixed"]],
            "operations":["GlobalJoin"] if p["fixed"] else ["Cyclic","Path","Return"]}

def snapshot(history):
    if history["status"]!="PASS": return None
    p=history["current"]
    return {"A":deepcopy(history['own_current']['A']),
            "H":deepcopy(history['own_current']['H']),
            "policy":"E1","interfaces":{"I_A":IDENT,"I_H":IDENT,"r":p["r"]},
            "Psi":{k:deepcopy(p[k]) for k in ("graph","transports","c","sections","operations")},
            "ordinary_own":{"A":["OrdinaryTrace","Pause"],"H":["OrdinaryTrace","Pause"]}}

def build_history(genesis,contexts,config):
    if not config.get("r_enabled"):
        missing=deepcopy(genesis); missing['events']=[e for e in missing['events'] if e['kind']!='RInterfaceEvent']
        trial=one.execute(missing)['branches']['H1']
        local={'A_exists':any(e['kind']=='AHistory' for e in missing['events']),
               'H_exists':any(e['kind']=='HHistory' for e in missing['events']),
               'r_present':any(e['kind']=='RInterfaceEvent' for e in missing['events']),
               'policy':trial['active_policy'],'joint':trial['cyclic']['status']}
        return {"status":"BLOCKED","reason":"NO_R","prefix":None,"journal":[],"current":None,
                "address_map":config["address_map"],'source_inputs':missing,'local_prefix':local}
    scenario=deepcopy(contexts["cases"][config["prefix"]])
    if config.get("bridge_phi_override"):
        scenario["bridge"]["phi"]=deepcopy(config["bridge_phi_override"])
    runtime=two.Session(genesis)
    runtime.admit(scenario["event"],scenario.get("bridge"))
    prefix=runtime.finish()
    if prefix["psi2"] is None:
        return {"status":"BLOCKED","reason":"NO_ADMITTED_PREFIX","prefix":prefix,"journal":[],"current":None,"address_map":config["address_map"]}
    ledger=one.Journal("own-history",prefix["journal"][-1]["digest"])
    ledger.append("PrefixExecuted",{"last_execution":digest(prefix["trace"]),"prefix_head":ledger.head},"E1")
    terminal=deepcopy(config.get("terminal"))
    if terminal:
        good=(terminal.get("source")=="H" and terminal.get("kind")=="HTerminalOwnChange" and
              terminal.get("origin")=="AUTHORED PREMISE" and terminal.get("parents")==["C0","prefix:executed"] and
              terminal["payload"].get("covenant_ref")=="C0" and one.bridge(terminal))
        ledger.append("TerminalHInput",terminal,"E1")
        if not good: return {"status":"BLOCKED","reason":"TERMINAL_SOURCE_OR_BETA","prefix":prefix,"journal":ledger.entries,"current":None,"address_map":config["address_map"]}
        a=prefix["psi2"]["a"]; h=terminal["payload"]["trace"]; r=prefix["psi2"]["r"]
    else:
        a=prefix["psi2"]["a"]; h=prefix["psi2"]["h"]; r=prefix["psi2"]["r"]
    current=psi(a,h,r,"Psi/current")
    a_event=next(e for e in genesis['events'] if e['id']=='A1')
    a_value=a_event['payload']['map'][a_event['payload']['before'].index([0,0])]
    h_start=genesis['branches']['H1']['event']['payload']
    h_value=h_start['map'][h_start['before'].index([0,0])]
    for own_event in ([prefix['candidate']]+([terminal] if terminal else [])):
        local=own_event['payload']
        h_value=local['map'][local['before'].index([0,h_value])]
    own_current={'A':{'domain':IDENT,'value':a_value,'trace':a,'law':'A/local/1'},
                 'H':{'domain':IDENT,'value':h_value,'trace':h,'law':'H/local/1'}}
    ledger.append("CurrentPsi",current,"E1")
    ledger.append("InheritedFormation",{"GlobalJoin":"PASS" if current["sections"] else "FAIL",
                                     "Cyclic":"BLOCKED" if current["sections"] else "PASS"},"E1")
    return {"status":"PASS","prefix":prefix,"prefix_input":scenario,"terminal":terminal,
            "current":current,"own_current":own_current,"address_map":config["address_map"],"journal":ledger.entries,
            "old_E0_verdict":prefix["old_E0_verdict"],"covenant":prefix["covenant"],"policy":"E1"}

def historical_witness(history,genesis):
    if history["status"]!="PASS": return {"status":"BLOCKED","reason":history.get("reason","NO_HISTORY")}
    prefix=history["prefix"]
    if prefix["admission"]["status"]!="PASS":
        return {"status":"BLOCKED","reason":"UNATTRIBUTED_HISTORY"}
    # Recompute full K/phi squares; never accept a supplied PRESERVED label.
    p1,p2=prefix["psi1"],prefix["psi2"]
    bridge=two.bridge_check(p1,p2,prefix["proposal"],prefix["candidate"],True)
    if bridge["strict"]!="PRESERVED":
        return {"status":"BLOCKED","reason":"NO_PRESERVED_HISTORICAL_TRANSPORT","bridge":bridge}
    if prefix["transfer"]["status"]!="PASS" or not prefix["trace"] or prefix["trace"][-1]["response"]["status"]!="PASS":
        return {"status":"BLOCKED","reason":"NO_EXECUTED_TRANSFER_RETURN"}
    records=genesis["events"]+[genesis["branches"]["H1"]["event"]]
    _,errors,unknown=one.sources(records)
    if errors or unknown: return {"status":"UNRESOLVED","reason":"H_A_R_SOURCE"}
    if history["address_map"]!=IDENT or history["current"]["r"]!=p2["r"]:
        return {"status":"BLOCKED","reason":"NO_CURRENT_ADDRESS_BRIDGE"}
    path=prefix["trace"][-1]["response"]["transition"]["path"]
    if path!=TRI: return {"status":"BLOCKED","reason":"HISTORICAL_CYCLE_DOMAIN"}
    loop=two.along(p1,path)
    f=prefix["proposal"]["phi"][0]
    frame=[f[0],f[loop[0]],f[loop[loop[0]]]]
    if sorted(frame)!=IDENT or loop[loop[loop[0]]]!=0:
        return {"status":"FAIL","reason":"NON_ORBIT"}
    successor=[0]*3
    for i,x in enumerate(frame): successor[x]=frame[(i+1)%3]
    transferred=prefix["transfer"]["token"]["state"]["x"]
    returned=prefix["trace"][-1]["response"]["transition"]["after"]["x"]
    if (transferred,returned)!=(frame[1],frame[2]):
        return {"status":"FAIL","reason":"ORBIT_NOT_EXECUTED"}
    return {"status":"PASS","scope":"historical orbit, NOT current monodromy",
            "path":path,"frame":frame,"successor":successor,"squares":bridge["squares"],
            "transfer":digest(prefix["transfer"]),"execution":digest(prefix["trace"][-1]),
            "preserved_source":prefix["candidate"]["id"],"address_map":history["address_map"],
            "current_c":history["current"]["c"],"origin":"AUTHORED PREMISE / STRUCTURALLY VERIFIED"}

def own_type(actor,w,snap):
    if w["status"]!="PASS" or snap is None:
        return {"status":"BLOCKED","reason":"HISTORICAL_WITNESS_REQUIRED","ordinary":["OrdinaryTrace","Pause"]}
    tau=w["successor"]; r=snap["interfaces"]["r"]
    trace=one.compose(one.inverse(r),one.compose(tau,r)) if actor=="H" else one.compose(
        snap["A"]["trace"],one.compose(tau,one.inverse(snap["A"]["trace"])))
    width=3 if actor=="H" else 2
    states=[[i,z] for i in IDENT for z in range(width)]
    embedding=[[trace[i],0 if actor=="H" else 1] for i in IDENT]
    ops={}
    if actor=="H":
        ops["Turn"]=[[i,(z+1)%3] for i,z in states]
        ops["Advance"]=[[trace[i],z] for i,z in states]
    else:
        ops["Seal"]=[[i,0] for i,z in states]
        ops["Readdress"]=[[trace[i],z] for i,z in states]
    return {"status":"PASS","actor":actor,"type":"HOrbitRefinement" if actor=="H" else "AAddressSeal",
            "scope":"own local object sort; not E2","witness":digest(w),"states":states,"beta":[i for i,z in states],
            "embedding":embedding,"trace":trace,"operations":ops,
            "law":actor+"/relational-local/2","ordinary":["OrdinaryTrace","Pause"],
            "new_beta_fibre_size":width}

def enact(history,formation,actor,event):
    snap=snapshot(history)
    if snap is None: return {"status":"BLOCKED","reason":"NO_CURRENT_CONTEXT","event":deepcopy(event)}
    before=deepcopy(snap[actor]); ledger=one.Journal("own-enactment/"+actor,history["journal"][-1]["digest"])
    ledger.append("Formation",formation,"E1")
    result={"status":"NOT ENACTED","event":None,"before":before,"after":deepcopy(before),"feedback":None,
            "operation_trace":[],"covenant_ref":"C0","eta_acceptance_ref":"C0","policy":"E1","unresolved":LIMITS}
    if event is not None:
        event=deepcopy(event); result["event"]=event; ledger.append("AuthoredOwnInput",event,"E1")
        keys={"id","kind","actor","source","origin","context","formation","action"}
        valid=(set(event)==keys and isinstance(event["id"],str) and bool(event["id"]) and
               event["id"] not in ("A0","A1","H0","h1","C0","R0") and
               event["kind"]=="OwnEnactment" and event["actor"]==actor and event["source"]==actor and
               event["context"]=="own:current:"+actor and event["formation"]=="own:formation:"+actor and
               event["action"] in ("relational","ordinary","Pause"))
        if not valid: result.update(status="FAIL",reason="OWN_SOURCE_OR_SCHEMA")
        elif event["origin"]!="AUTHORED PREMISE": result.update(status="UNRESOLVED",reason="OWN_ORIGIN")
        elif event["action"]=="Pause": result.update(status="PASS",reason="PAUSE")
        elif event["action"]=="relational" and formation["status"]!="PASS":
            result.update(status="BLOCKED",reason="TYPE_NOT_FORMED")
        else:
            if event["action"]=="relational":
                definition=formation
                state=definition["embedding"][before["value"]]
                after={"domain":definition["states"],"value":state,"trace":definition["trace"],
                       "law":definition["law"],"beta":definition["beta"],"operations":definition["operations"]}
                result["after"]=after
                result['embedding_value']=deepcopy(state)
                result["beta_equation"]=[definition["embedding"][i][0]==definition["trace"][i] for i in IDENT]
                at=deepcopy(state)
                for name in (["Turn"] if actor=='H' else ["Seal"]):
                    table=definition['operations'][name]
                    nxt=table[definition["states"].index(at)]
                    result["operation_trace"].append({"operation":name,"before":at,"after":nxt})
                    at=nxt
                result['after']['value']=deepcopy(at)
                result["local_install"]={"actor":actor,"from":before["law"],"to":definition["law"],
                                         "formation":digest(definition),"event":event["id"]}
            else:
                result["after"]["value"]=before["trace"][before["value"]]
            a=result["after"]["trace"] if actor=="A" else snap["A"]["trace"]
            h=result["after"]["trace"] if actor=="H" else snap["H"]["trace"]
            newpsi=psi(a,h,snap["interfaces"]["r"],"Psi/feedback/"+actor)
            result["feedback"]=newpsi
            if not newpsi["sections"]:
                raw=one.make_psi(a,h,snap["interfaces"]["r"],{})
                machine=one.Cyclic(raw,"E1"); op=machine.returning()
                result["joint_execution"]={"status":"PASS","operation":"Return","trace":op}
            else:
                result["joint_execution"]={"status":"PASS","operation":"GlobalJoin","section":newpsi["sections"][0]}
            result.update(status="PASS",reason="SELF_ENACTED_OWN_CHANGE")
    ledger.append("OwnOutcome",deepcopy(result),"E1")
    result["journal"]=ledger.entries
    return result

def build(genesis,contexts,inputs,choice_loader):
    histories={name:build_history(genesis,contexts,cfg) for name,cfg in inputs["histories"].items()}
    snapshots={name:snapshot(h) for name,h in histories.items()}
    witnesses={name:historical_witness(h,genesis) for name,h in histories.items()}
    formations={name:{a:own_type(a,witnesses[name],snapshots[name]) for a in ("A","H")} for name in histories}
    # Separate actual authored source is read only after possibilities are formed.
    choices=choice_loader(deepcopy(formations))
    enacted={}
    for name,choice in choices.items():
        hist=choice["history"]; actor=choice["actor"]
        enacted[name]=enact(histories[hist],formations[hist][actor],actor,choice["event"])
    return {"schema":"source-x-own-feedback/3","histories":histories,"snapshots":snapshots,
            "witnesses":witnesses,"formations":formations,"enactments":enacted,
            "snapshot_equal":snapshots["alpha"]==snapshots["beta"],
            "history_equal":digest(histories["alpha"])==digest(histories["beta"]),
            "formal_novelty_against_E0plus":"FAIL","unresolved":LIMITS}

