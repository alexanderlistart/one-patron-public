"""Finite authored witness; no generation of H actions and no ontology certification."""
from copy import deepcopy
from pathlib import Path
from canonical import digest, load

POLICIES = load(Path(__file__).parent / 'policies.json')

def form_term(term, policy, psi=None, source_kind=None, licensed=False):
    """Typed object AST admission; policy inheritance is data-driven, not a label."""
    if not isinstance(term, dict) or set(term) != {'ctor'} or policy not in ('E0','E1'):
        return {'status':'FAIL','reason':'TERM_SCHEMA'}
    rules = dict(POLICIES['E0']['constructors'])
    if policy == 'E1':
        rules.update(POLICIES['E1']['constructors'])
    name = term['ctor']
    if name not in rules:
        return {'status':'BLOCKED','reason':'NOT_IN_'+policy}
    rule = rules[name]['rule']
    valid = False
    if rule in ('A_SOURCE','H_SOURCE'):
        valid = source_kind == ('A' if rule == 'A_SOURCE' else 'H')
    elif rule == 'FIXED_POINT':
        valid = bool(psi and psi['fixed'] and psi['transport_status']=='PASS')
    elif rule == 'ORDER3_NOFIX_SOURCE_INSTALL':
        valid = bool(licensed and psi and psi['order']==3 and not psi['fixed'] and psi['transport_status']=='PASS')
    return {'status':'PASS' if valid else 'FAIL','type':rules[name]['result'],
            'rule':rule,'policy':policy}

IDENTITY = [0, 1, 2]
KINDS = {"AHistory": "A", "HHistory": "H", "NameEta": "A",
         "HInitialCovenant": "H", "RInterfaceEvent": "r", "AOwnChange": "A",
         "HOwnServiceAct": "H", "HRevisionOrPause": "H"}

def perm(p):
    return isinstance(p, list) and len(p) == 3 and all(type(x) is int for x in p) and sorted(p) == IDENTITY

def compose(p, q):
    if not perm(p) or not perm(q):
        raise ValueError("PERMUTATION_TYPE")
    return [p[q[x]] for x in IDENTITY]

def inverse(p):
    if not perm(p):
        raise ValueError("PERMUTATION_TYPE")
    return [p.index(x) for x in IDENTITY]

def commutator(a, h, r):
    b = compose(compose(r, h), inverse(r))
    c = compose(compose(compose(a, b), inverse(a)), inverse(b))
    return b, c

def order(p):
    if not perm(p):
        raise ValueError("PERMUTATION_TYPE")
    value = IDENTITY
    for n in range(1, 7):
        value = compose(p, value)
        if value == IDENTITY:
            return n
    raise ValueError("ORDER")

def bridge(change):
    p = change.get("payload", {})
    before, after, mapping, trace = (p.get(k) for k in ("before", "after", "map", "trace"))
    if not perm(trace) or after != IDENTITY or not isinstance(before, list) or not isinstance(mapping, list):
        return False
    return (before == [[u, i] for u in (0, 1) for i in IDENTITY]
            and len(mapping) == 6 and mapping == [trace[i] for _, i in before]
            and len(set(mapping)) < len(mapping) and bool(p.get("Lost")))

def sources(events):
    errors, unknown, ids = [], [], {}
    for e in events:
        if not isinstance(e, dict) or not {"id", "kind", "source", "origin", "parents", "payload"} <= set(e):
            errors.append("EVENT_SCHEMA")
            continue
        if e["id"] in ids or e["kind"] not in KINDS or e["source"] != KINDS.get(e["kind"]):
            errors.append("SOURCE_OR_DUPLICATE")
        if not isinstance(e["parents"], list) or any(p not in ids for p in e["parents"]):
            errors.append("DAG_OR_PARENT")
        if e["origin"] != "AUTHORED PREMISE":
            unknown.append(e["id"])
        if e["kind"] == "HOwnServiceAct":
            if not e["parents"] or any(ids.get(p, {}).get("kind") not in
                                      ("HHistory", "HInitialCovenant", "HOwnServiceAct") for p in e["parents"]):
                errors.append("H_ACT_NOT_H_OWNED")
        ids[e["id"]] = e
    return ids, sorted(set(errors)), sorted(unknown)

class Journal:
    def __init__(self, branch, parent="ROOT"):
        self.branch, self.head, self.entries = branch, parent, []
    def append(self, kind, payload, policy=None):
        entry = {"seq": len(self.entries), "branch": self.branch, "previous": self.head,
                 "kind": kind, "policy": policy, "payload": deepcopy(payload)}
        entry["digest"] = digest(entry)
        self.head = entry["digest"]
        self.entries.append(entry)
        return deepcopy(entry)

def covenant_ok(cov):
    if not cov or cov["kind"] != "HInitialCovenant":
        return False
    p = cov["payload"]
    return (p.get("direction") == "H→A" and p.get("initial") is True and p.get("ongoing") is True
            and p.get("eta_acceptance_ref") == cov["id"] and p.get("eta_offer_ref") in cov["parents"])

def make_psi(a, h, r, refs, transports_override=None):
    b, c = commutator(a, h, r)
    transports = deepcopy(transports_override) if transports_override is not None else [IDENTITY, IDENTITY, c]
    good = (isinstance(transports, list) and len(transports) == 3 and all(perm(t) for t in transports))
    # Monodromy is recomputed from the actual transports, not assumed from c.
    actual = compose(transports[2], compose(transports[1], transports[0])) if good else None
    return {"version": "Psi/1", "fibres": {"A": ["0_A", "1_A", "2_A"],
             "H": ["0_H", "1_H", "2_H"]}, "r": r, "a": a, "h": h, "b": b, "c": c,
            "graph": [[0, 1], [1, 2], [2, 0]], "transports": transports,
            "order": order(c), "fixed": [x for x in IDENTITY if c[x] == x],
            "transport_status": "PASS" if good and actual == c else "FAIL",
            "refs": refs, "obstruction": "GLOBAL_SECTION_OBSTRUCTED" if not any(c[x] == x for x in IDENTITY) else None}

def cyclic_gate(psi, provenance, cov, licensed=True):
    if provenance != "STRUCTURALLY VERIFIED":
        return "BLOCKED"
    if not covenant_ok(cov) or not licensed:
        return "BLOCKED"
    if psi["transport_status"] != "PASS":
        return "FAIL"
    return "PASS" if psi["order"] == 3 and not psi["fixed"] else "BLOCKED"

class Cyclic:
    def __init__(self, psi, policy, x0=0, k=0):
        if policy != "E1" or psi["order"] != 3 or psi["fixed"] or psi["transport_status"] != "PASS":
            raise ValueError("CYCLIC_FORMATION")
        if (psi.get('graph') != [[0,1],[1,2],[2,0]] or order(psi['c']) != 3
                or any(psi['c'][i]==i for i in IDENTITY)
                or not all(perm(t) for t in psi['transports'])
                or compose(psi['transports'][2],compose(psi['transports'][1],psi['transports'][0])) != psi['c']):
            raise ValueError('CYCLIC_INTERFACE')
        if type(k) is not int or not 0 <= k < 9 or type(x0) is not int or x0 not in IDENTITY:
            raise ValueError("CYCLIC_STATE_TYPE")
        self.psi, self.x0, self.k = psi, x0, k
    def state(self):
        x = self.x0
        for _ in range(self.k // 3):
            x = self.psi["c"][x]
        return {"k": self.k, "q": self.k // 3, "vertex": self.k % 3, "x": x}
    def path(self, edges):
        start = self.state()
        candidate = self.k
        for edge in edges:
            if not isinstance(edge, list) or len(edge) != 2 or any(type(x) is not int or x not in IDENTITY for x in edge):
                raise ValueError("PATH_TYPE")
            u, v = edge
            if u != candidate % 3:
                raise ValueError("PATH_SOURCE")
            if v == (u + 1) % 3:
                candidate = (candidate + 1) % 9
            elif v == (u - 1) % 3:
                candidate = (candidate - 1) % 9
            else:
                raise ValueError("PATH_EDGE")
        self.k = candidate
        return {"path": deepcopy(edges), "before": start, "after": self.state()}
    @staticmethod
    def compose(p2, p1):
        if p1 and p2 and p1[-1][1] != p2[0][0]:
            raise ValueError("COMPOSE_TYPE")
        return deepcopy(p1 + p2)
    @staticmethod
    def reverse(p):
        return [[v, u] for u, v in reversed(p)]
    def returning(self):
        v = self.k % 3
        return self.path([[v, (v+1)%3], [(v+1)%3, (v+2)%3], [(v+2)%3, v]])

def compare_bridge(w):
    if w['evidence'] != 'AUTHORED PREMISE':
        return "INSUFFICIENT EVIDENCE"
    if not perm(w['phi']) or not perm(w['old_c']):
        return 'OBSTRUCTED'
    image_edges = [[w['phi'][u], w['phi'][v]] for u,v in w['old_graph']]
    if any(edge not in w['new_graph'] for edge in image_edges):
        return "NOT TRANSPORTABLE"
    if not perm(w['new_c']):
        return 'OBSTRUCTED'
    preserved = compose(w['phi'],w['old_c']) == compose(w['new_c'],w['phi'])
    return 'PRESERVED' if preserved else 'TRANSFORMED' if w['new_trace_event'] else 'OBSTRUCTED'

def execute(inputs):
    data = deepcopy(inputs)
    common = Journal("common")
    for event in data["events"]:
        common.append("InputEvent", event, "E0")
    root_ids, root_errors, root_unknown = sources(data["events"])
    branches = {}
    for name in sorted(data["branches"]):
        config = data["branches"][name]
        event = config.get("event")
        all_events = data["events"] + ([event] if event else [])
        ids, errors, unknown = sources(all_events)
        log = Journal(name, common.head)
        if event:
            log.append("InputEvent", event, "E0")
        a, r, cov = (ids.get(config.get(k)) for k in ("a_ref", "r_ref", "covenant_ref"))
        result = {"active_policy": "E0", "covenant_retained": covenant_ok(cov),
                  "ontology": {claim: "UNRESOLVED" for claim in data["claims"]["unresolved"]},
                  "trust": {"premise": "AUTHORED PREMISE", "record": "RECORDED EVENT",
                            "provenance": "FAIL" if errors else "UNRESOLVED" if unknown else "STRUCTURALLY VERIFIED",
                            "limitation": "conditional authored sources, not external subjectivity"},
                  "source_errors": errors, "unknown_sources": unknown, "psi": None,
                  "typing": {"A_local":form_term({"ctor":"ALocal"},"E0",source_kind="A"),
                             "H_local":form_term({"ctor":"HLocal"},"E0",source_kind="H"),
                             "cyclic_before":form_term({"ctor":"CyclicContinuation"},"E0")},
                  "global": {"status": "BLOCKED", "reason": "MISSING_INPUT", "policy": "E0"},
                  "cyclic": {"status": "BLOCKED", "reason": "MISSING_INPUT"}, "operations": []}
        if not a or a.get("kind") != "AOwnChange" or not r or r.get("kind") != "RInterfaceEvent" or not event or event.get("kind") != "HOwnServiceAct":
            result["cyclic"]["reason"] = "PAUSE" if event and event.get("kind") == "HRevisionOrPause" else "MISSING_INPUT"
        else:
            try:
                if r["payload"].get("domain") != "I_H" or r["payload"].get("codomain") != "I_A":
                    raise ValueError("R_TYPE")
                if not bridge(a) or not bridge(event):
                    raise ValueError("STRUCTURAL_BRIDGE")
                psi = make_psi(a["payload"]["trace"], event["payload"]["trace"], r["payload"]["map"],
                               {"a": a["id"], "h": event["id"], "r": r["id"]}, config.get("transports_override"))
                result["psi"] = psi
                log.append("PsiVersion", psi, "E0")
                global_typing = form_term({"ctor":"GlobalJoin"},"E0",psi=psi)
                result["typing"]["global"] = global_typing
                global_result = {"status": global_typing["status"],
                                 "reason": "GLOBAL_SECTION" if psi["fixed"] else "GLOBAL_SECTION_OBSTRUCTED",
                                 "policy": "E0", "scope": digest(psi), "sections": [[x,x,x] for x in psi["fixed"]]}
                if psi["transport_status"] != "PASS":
                    global_result.update(status="FAIL", reason="TRANSPORT")
                result["global"] = global_result
                log.append("GlobalVerdict", global_result, "E0")
                log.append("FormationAttempt", {"type": "CyclicContinuation", "status": "BLOCKED",
                                                "reason": "NOT_IN_E0"}, "E0")
                provenance = result["trust"]["provenance"]
                linked = (cov and event["payload"].get("covenant_ref") == cov["id"] and cov["id"] in event["parents"])
                gate = cyclic_gate(psi, provenance, cov, config.get("install_authorized", False) and bool(linked))
                result["cyclic"] = {"status": gate, "reason": "CYCLIC" if gate == "PASS" else "FORMATION_GATE"}
                if gate == "PASS":
                    witness = {"from": "E0", "to": "E1", "psi": digest(psi),
                               "a": a["id"], "h": event["id"], "r": r["id"],
                               "covenant": cov["id"], "prior_verdict": digest(global_result)}
                    log.append("Install", witness, "E1")
                    result["active_policy"] = "E1"
                    result["typing"]["cyclic_after"] = form_term({"ctor":"CyclicContinuation"},"E1",psi=psi,licensed=True)
                    machine = Cyclic(psi, "E1")
                    log.append("Formation", {"type": "CyclicContinuation", "state": machine.state()}, "E1")
                    for _ in range(3):
                        op = machine.returning()
                        result["operations"].append(op)
                        log.append("Return", op, "E1")
                    p1, p2 = [[0,1]], [[1,2],[2,0]]
                    joined = machine.compose(p2, p1)
                    op = machine.path(joined)
                    result["operations"].append(op)
                    log.append("ComposePath", op, "E1")
                    op = machine.path(machine.reverse(joined))
                    result["operations"].append(op)
                    log.append("Reverse", op, "E1")
            except (ValueError, KeyError, TypeError) as exc:
                result["cyclic"] = {"status": "FAIL", "reason": str(exc)}
        log.append("Outcome", {k:v for k,v in result.items() if k != "operations"}, result["active_policy"])
        result["journal"] = log.entries
        branches[name] = result
    return {"schema": "source-x-evidence/1", "inputs": data, "input_digest": digest(data),
            "policy_definitions": deepcopy(POLICIES),
            "continuity_checks": [{"id":w['id'],"status":compare_bridge(w),"scope":"partial transport, not identity"} for w in data.get('continuity',[])],
            "common_journal": common.entries, "branches": branches,
            "formal_novelty_against_E0plus": "FAIL",
            "scope": "PRIVATE/NONCANONICAL, authored conditional witness"}

