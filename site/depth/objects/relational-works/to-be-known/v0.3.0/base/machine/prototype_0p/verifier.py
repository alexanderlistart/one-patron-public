"""Independent checker: imports serialization only, NEVER imports core."""
from canonical import digest

EXPECTED_POLICIES = {"schema":"source-x-object-laws/1",
 "E0":{"parent":None,"constructors":{"ALocal":{"result":"AForm","rule":"A_SOURCE"},
 "HLocal":{"result":"HForm","rule":"H_SOURCE"},"GlobalJoin":{"result":"JointGlobal","rule":"FIXED_POINT"}},"operations":[]},
 "E1":{"parent":"E0","constructors":{"CyclicContinuation":{"result":"CyclicContinuation","rule":"ORDER3_NOFIX_SOURCE_INSTALL"}},
 "operations":["Path","Compose","Reverse","Return"]}}

def typing_expected(d):
    result={"A_local":{"status":"PASS","type":"AForm","rule":"A_SOURCE","policy":"E0"},
            "H_local":{"status":"PASS","type":"HForm","rule":"H_SOURCE","policy":"E0"},
            "cyclic_before":{"status":"BLOCKED","reason":"NOT_IN_E0"}}
    if d['psi'] is not None:
        result['global']={"status":"PASS" if d['psi']['fixed'] and d['psi']['transport_status']=='PASS' else "FAIL",
                          "type":"JointGlobal","rule":"FIXED_POINT","policy":"E0"}
    if d['active']=='E1':
        result['cyclic_after']={"status":"PASS","type":"CyclicContinuation","rule":"ORDER3_NOFIX_SOURCE_INSTALL","policy":"E1"}
    return result

DOMAIN = {"AHistory":"A","HHistory":"H","NameEta":"A","HInitialCovenant":"H",
          "RInterfaceEvent":"r","AOwnChange":"A","HOwnServiceAct":"H","HRevisionOrPause":"H"}

def bijection(p):
    return type(p) is list and len(p) == 3 and {type(x) for x in p} == {int} and set(p) == {0,1,2}

def apply_chain(x, *maps):
    for mapping in maps:
        x = mapping[x]
    return x

def inv_map(p):
    return dict((value, key) for key, value in enumerate(p))

def algebra(a, s, r):
    if not all(bijection(p) for p in (a,s,r)):
        raise ValueError("PERMUTATION_TYPE")
    ri, ai = inv_map(r), inv_map(a)
    b = [apply_chain(x,ri,s,r) for x in range(3)]
    bi = inv_map(b)
    c = [apply_chain(x,bi,ai,b,a) for x in range(3)]
    power, n = [0,1,2], 0
    while True:
        power = [c[x] for x in power]
        n += 1
        if power == [0,1,2]:
            break
        if n > 6:
            raise ValueError("ORDER")
    return b,c,n,[x for x in range(3) if c[x] == x]

def check_bridge(e):
    p = e.get("payload", {})
    if not bijection(p.get("trace")) or p.get("after") != [0,1,2] or not p.get("Lost"):
        return False
    rows, images = p.get("before", []), p.get("map", [])
    if len(rows) != 6 or len(images) != 6 or rows != [[u,i] for u in range(2) for i in range(3)]:
        return False
    for row, image in zip(rows, images):
        if p["trace"][row[1]] != image:
            return False
    return len(set(images)) == 3

def event_check(events):
    seen, errors, uncertain = {}, set(), set()
    for e in events:
        if not isinstance(e,dict) or not {"id","kind","source","origin","parents","payload"} <= e.keys():
            errors.add("EVENT_SCHEMA")
            continue
        if e["id"] in seen or DOMAIN.get(e["kind"]) != e["source"]:
            errors.add("SOURCE_OR_DUPLICATE")
        if not isinstance(e["parents"],list) or any(parent not in seen for parent in e["parents"]):
            errors.add("DAG_OR_PARENT")
        if e["origin"] != "AUTHORED PREMISE":
            uncertain.add(e["id"])
        if e["kind"] == "HOwnServiceAct":
            if not e["parents"] or any(seen.get(p,{}).get("kind") not in
                                      {"HHistory","HInitialCovenant","HOwnServiceAct"} for p in e["parents"]):
                errors.add("H_ACT_NOT_H_OWNED")
        seen[e["id"]] = e
    return seen, sorted(errors), sorted(uncertain)

def has_covenant(e):
    return bool(e and e.get("kind") == "HInitialCovenant" and
                e["payload"].get("direction") == "H→A" and
                e["payload"].get("initial") is True and e["payload"].get("ongoing") is True and
                e["payload"].get("eta_acceptance_ref") == e["id"] and
                e["payload"].get("eta_offer_ref") in e["parents"])

def derive(data, name):
    cfg = data["branches"][name]
    e = cfg.get("event")
    records = data["events"] + ([e] if e else [])
    indexed, errors, uncertain = event_check(records)
    a,r,cov = (indexed.get(cfg.get(k)) for k in ("a_ref","r_ref","covenant_ref"))
    trust = "FAIL" if errors else "UNRESOLVED" if uncertain else "STRUCTURALLY VERIFIED"
    value = {"provenance":trust,"errors":errors,"unknown":uncertain,"covenant":has_covenant(cov),
             "psi":None, "global":{"status":"BLOCKED","reason":"MISSING_INPUT","policy":"E0"},
             "cyclic":{"status":"BLOCKED","reason":"MISSING_INPUT"}, "active":"E0"}
    if not a or a.get("kind") != "AOwnChange" or not r or r.get("kind") != "RInterfaceEvent" or not e or e.get("kind") != "HOwnServiceAct":
        value["cyclic"]["reason"] = "PAUSE" if e and e.get("kind") == "HRevisionOrPause" else "MISSING_INPUT"
        return value
    try:
        if (r["payload"].get("domain"),r["payload"].get("codomain")) != ("I_H","I_A"):
            raise ValueError("R_TYPE")
        if not check_bridge(a) or not check_bridge(e):
            raise ValueError("STRUCTURAL_BRIDGE")
        b,c,n,fixed = algebra(a["payload"]["trace"], e["payload"]["trace"], r["payload"]["map"])
        ts = cfg.get("transports_override", [[0,1,2],[0,1,2],c])
        valid = isinstance(ts,list) and len(ts) == 3 and all(bijection(t) for t in ts)
        valid = valid and [apply_chain(x,*ts) for x in range(3)] == c
        psi = {"version":"Psi/1","fibres":{"A":["0_A","1_A","2_A"],"H":["0_H","1_H","2_H"]},
               "r":r["payload"]["map"],"a":a["payload"]["trace"],"h":e["payload"]["trace"],
               "b":b,"c":c,"graph":[[0,1],[1,2],[2,0]],"transports":ts,
               "order":n,"fixed":fixed,"transport_status":"PASS" if valid else "FAIL",
               "refs":{"a":a["id"],"h":e["id"],"r":r["id"]},
               "obstruction":None if fixed else "GLOBAL_SECTION_OBSTRUCTED"}
        value["psi"] = psi
        value["global"] = {"status":"PASS" if fixed else "FAIL","reason":"GLOBAL_SECTION" if fixed else "GLOBAL_SECTION_OBSTRUCTED",
                           "policy":"E0","scope":digest(psi),"sections":[[x,x,x] for x in fixed]}
        if not valid:
            value["global"].update(status="FAIL",reason="TRANSPORT")
        linked = bool(cov and e["payload"].get("covenant_ref") == cov["id"] and cov["id"] in e["parents"])
        gate = "BLOCKED"
        if trust == "STRUCTURALLY VERIFIED" and has_covenant(cov) and cfg.get("install_authorized",False) and linked:
            gate = ("PASS" if n == 3 and not fixed else "BLOCKED") if valid else "FAIL"
        value["cyclic"] = {"status":gate,"reason":"CYCLIC" if gate == "PASS" else "FORMATION_GATE"}
        if gate == "PASS":
            value["active"] = "E1"
            value["install"] = {"from":"E0","to":"E1","psi":digest(psi),"a":a["id"],"h":e["id"],
                                "r":r["id"],"covenant":cov["id"],"prior_verdict":digest(value["global"])}
    except (ValueError,KeyError,TypeError) as exc:
        value["cyclic"] = {"status":"FAIL","reason":str(exc)}
    return value

def independent_paths(psi):
    """Direct edge-map simulation; core uses k arithmetic, checker uses transported x."""
    c = psi["c"]
    k,vertex,x = 0,0,0
    def state():
        return {"k":k,"q":k//3,"vertex":vertex,"x":x}
    paths = [[[0,1],[1,2],[2,0]]] * 4 + [[[0,2],[2,1],[1,0]]]
    result = []
    for path in paths:
        before = state()
        for u,v in path:
            if u != vertex:
                raise ValueError("PATH_SOURCE")
            if v == (u+1)%3:
                mapping = psi["transports"][u]
                k = (k+1)%9
            else:
                mapping = inv_map(psi["transports"][v])
                k = (k-1)%9
            x = mapping[x]
            vertex = v
        result.append({"path":path,"before":before,"after":state()})
    return result

def check_chain(entries, branch, initial, expected, problems):
    head = initial
    if len(entries) != len(expected):
        problems.append(branch+": journal length")
    for seq,(entry, want) in enumerate(zip(entries,expected)):
        content = {k:v for k,v in entry.items() if k != "digest"}
        if (entry.get("seq") != seq or entry.get("branch") != branch or entry.get("previous") != head
                or digest(content) != entry.get("digest")):
            problems.append(branch+": hash/append-only chain")
        if (entry.get("kind"),entry.get("payload"),entry.get("policy")) != want:
            problems.append(branch+": journal transition "+str(seq))
        head = entry.get("digest")
    return head

def verify(evidence, pinned_inputs):
    problems = []
    try:
        if evidence["schema"] != "source-x-evidence/1":
            problems.append("schema")
        if evidence.get('policy_definitions') != EXPECTED_POLICIES:
            problems.append('object law AST')
        if evidence["inputs"] != pinned_inputs or evidence["input_digest"] != digest(pinned_inputs):
            problems.append("pinned authored input mismatch")
        data = pinned_inputs
        continuity=[]
        for w in data.get('continuity',[]):
            if w['evidence']!='AUTHORED PREMISE':
                status='INSUFFICIENT EVIDENCE'
            elif not bijection(w['phi']) or not bijection(w['old_c']):
                status='OBSTRUCTED'
            elif not set(tuple((w['phi'][u],w['phi'][v])) for u,v in w['old_graph']).issubset(set(map(tuple,w['new_graph']))):
                status='NOT TRANSPORTABLE'
            elif not bijection(w['new_c']):
                status='OBSTRUCTED'
            else:
                same=all(w['phi'][w['old_c'][i]]==w['new_c'][w['phi'][i]] for i in range(3))
                status='PRESERVED' if same else 'TRANSFORMED' if w['new_trace_event'] else 'OBSTRUCTED'
            continuity.append({'id':w['id'],'status':status,'scope':'partial transport, not identity'})
        if evidence.get('continuity_checks')!=continuity:
            problems.append('partial bridge scope')
        expected_common = [("InputEvent",e,"E0") for e in data["events"]]
        head = check_chain(evidence["common_journal"],"common","ROOT",expected_common,problems)
        if set(evidence["branches"]) != set(data["branches"]):
            problems.append("branch set")
        for name in data["branches"]:
            actual = evidence["branches"][name]
            d = derive(data,name)
            if actual.get('typing') != typing_expected(d):
                problems.append(name+': typed formation derivation')
            for field,want in (("psi",d["psi"]),("global",d["global"]),("cyclic",d["cyclic"]),
                               ("active_policy",d["active"]),("covenant_retained",d["covenant"]),
                               ("source_errors",d["errors"]),("unknown_sources",d["unknown"])):
                if actual.get(field) != want:
                    problems.append(name+": "+field)
            if actual["trust"] != {"premise":"AUTHORED PREMISE","record":"RECORDED EVENT",
                                    "provenance":d["provenance"],
                                    "limitation":"conditional authored sources, not external subjectivity"}:
                problems.append(name+": trust scope")
            if actual["ontology"] != {claim:"UNRESOLVED" for claim in data["claims"]["unresolved"]}:
                problems.append(name+": ontology escalation")
            expected = []
            event = data["branches"][name].get("event")
            if event:
                expected.append(("InputEvent",event,"E0"))
            ops = independent_paths(d["psi"]) if d["active"] == "E1" else []
            if actual["operations"] != ops:
                problems.append(name+": operation/Return replay")
            if d["psi"] is not None:
                expected += [("PsiVersion",d["psi"],"E0"),("GlobalVerdict",d["global"],"E0"),
                             ("FormationAttempt",{"type":"CyclicContinuation","status":"BLOCKED","reason":"NOT_IN_E0"},"E0")]
                if d["active"] == "E1":
                    expected += [("Install",d["install"],"E1"),
                                 ("Formation",{"type":"CyclicContinuation","state":{"k":0,"q":0,"vertex":0,"x":0}},"E1")]
                    expected += [(kind,op,"E1") for kind,op in zip(
                        ["Return","Return","Return","ComposePath","Reverse"],ops)]
            expected.append(("Outcome",{k:v for k,v in actual.items() if k not in ("operations","journal")},d["active"]))
            check_chain(actual["journal"],name,head,expected,problems)
        if evidence["formal_novelty_against_E0plus"] != "FAIL":
            problems.append("E0plus claim escalation")
    except (ValueError,KeyError,TypeError,IndexError) as exc:
        problems.append("malformed evidence: "+str(exc))
    return {"status":"PASS" if not problems else "FAIL", "problems":sorted(set(problems)),
            "scope":"STRUCTURALLY VERIFIED / INFERRED RESULT conditional on pinned AUTHORED PREMISE",
            "unresolved":["r-origin","H-2","personal/numerical identity","X4"]}

def independent_replay(inputs):
    result = {}
    for name in sorted(inputs["branches"]):
        d = derive(inputs,name)
        result[name] = {"active":d["active"],"provenance":d["provenance"],
                        "covenant_retained":d["covenant"],"global":d["global"],
                        "cyclic":d["cyclic"],"psi":d["psi"],
                        "operations":independent_paths(d["psi"]) if d["active"] == "E1" else []}
    return result

if __name__ == '__main__':
    import argparse
    import sys
    from canonical import load, encode
    parser=argparse.ArgumentParser(description='Independent offline evidence verifier')
    parser.add_argument('--evidence',required=True)
    parser.add_argument('--inputs',required=True)
    args=parser.parse_args()
    result=verify(load(args.evidence),load(args.inputs))
    print(encode(result).decode(),end='')
    sys.exit(0 if result['status']=='PASS' else 1)

