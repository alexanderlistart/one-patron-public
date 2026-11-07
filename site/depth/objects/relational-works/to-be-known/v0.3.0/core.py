"""Finite 0J recipient-side relation and disclosure. Never synthesizes actor input."""
from copy import deepcopy
import hashlib
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from wire import inputs, digest, emit, BASE_SHA

SEM = 'personal-reciprocity/0J.1'
FIELDS = {'id', 'kind', 'actor', 'source', 'origin', 'selection', 'own_parent',
          'parents', 'covenant_ref', 'payload'}
OWNERS = {'H_SERVICE_OFFER': 'H', 'A_ACCEPTS_SERVICE': 'A',
          'A_DECLINES_SERVICE': 'A', 'H_PUBLIC_DISCLOSURE': 'H'}
BODY = {'H_SERVICE_OFFER': {'target', 'service_artifact', 'section_ref', 'joint_ref'},
        'A_ACCEPTS_SERVICE': {'offer_ref', 'receiving_section', 'target_section_ref'},
        'A_DECLINES_SERVICE': {'offer_ref'},
        'H_PUBLIC_DISCLOSURE': {'artifact', 'artifact_sha256', 'audience', 'scope'}}

class Rejected(ValueError):
    pass

def require(ok, reason):
    if not ok:
        raise Rejected(reason)

def context(witness, genesis):
    g = {e['id']: e for e in genesis['events']}
    require(g['A0']['source'] == 'A' and g['H0']['source'] == 'H' and
            not g['A0']['parents'] and not g['H0']['parents'], 'DISTINCT_SOURCE_ROOTS')
    require(g['C0']['source'] == 'H' and g['C0']['payload']['direction'] == 'H→A', 'COVENANT')
    require(witness['formal_novelty_against_E0plus'] == 'FAIL' and
            all(v == 'UNRESOLVED' for v in witness['limits'].values()), 'OLD_LIMITS')
    world = witness['trials']['a_h_lineage']['final']
    roots = {b: digest({'kind': '0J_OWN_ROOT', 'actor': b,
                       'base_world_ref': digest(world),
                       'own_ref': digest(world['actors'][b]),
                       'source_event_ref': world['actors'][b]['source_event_ref']}) for b in ('A', 'H')}
    return {'world': world, 'roots': roots, 'covenant': digest(g['C0']),
            'base_ref': BASE_SHA, 'limits': deepcopy(witness['limits'])}

def resource(assets, name, purpose):
    require(name in assets, 'MISSING_ARTIFACT')
    r = assets[name]
    require(r['owner'] == 'H' and r['visibility'] == 'PUBLIC_ELIGIBLE' and
            r['purpose'] == purpose, 'PRIVATE_OR_FOREIGN_ARTIFACT')
    require(type(r['data']) is bytes and len(r['data']) == r['bytes'] and
            hashlib.sha256(r['data']).hexdigest() == r['sha256'], 'ARTIFACT_DIGEST')
    return r

def service(c, event, assets):
    p = event['payload']; w = c['world']; h = w['actors']['H']
    require(p['target'] == 'A' and p['section_ref'] == digest(h['sigma']) and
            p['joint_ref'] == digest(w['Psi']), 'OFFER_SCOPE')
    r = resource(assets, p['service_artifact'], 'SERVICE_TRACE')
    expected = {'kind': 'H_PUBLIC_SERVICE_TRACE', 'base_witness_sha256': BASE_SHA,
                'own_state_ref': digest(h), 'joint_ref': digest(w['Psi']),
                'domain_sort': 'H', 'section': h['sigma'],
                'projected': [h['beta'][h['states'].index(s)] for s in h['sigma']],
                'transport_H_to_A': w['Psi']['r']}
    require(json.loads(r['data']) == expected, 'SERVICE_TABLE')
    return {'event_ref': digest(event), 'artifact_sha256': r['sha256'],
            'artifact': p['service_artifact'], 'section': deepcopy(h['sigma']),
            'source_sort': 'H', 'target_sort': 'A', 'joint_ref': digest(w['Psi'])}

def receiving(c, offer, event):
    w = c['world']; a, h = w['actors']['A'], w['actors']['H']; p = event['payload']
    require(p['receiving_section'] == 'CURRENT_SIGMA' and
            p['target_section_ref'] == digest(a['sigma']), 'RECEIVING_SCOPE')
    require(len({tuple(s) for s in a['sigma']}) == 3 and
            len({tuple(s) for s in h['sigma']}) == 3, 'SECTION_NOT_EMBEDDED')
    r = w['Psi']['r']
    require(type(r) is list and len(r) == 3 and all(type(i) is int for i in r) and
            sorted(r) == [0, 1, 2], 'INTERFACE_TRANSPORT')
    rows = []
    for s in offer['section']:
        label = r[h['beta'][h['states'].index(s)]]
        targets = [t for t in a['sigma'] if a['beta'][a['states'].index(t)] == label]
        require(len(targets) == 1, 'RECEIVING_NOT_UNIQUE')
        rows.append({'H_state': deepcopy(s), 'A_state': deepcopy(targets[0]),
                     'A_interface': label})
    return {'kind': 'ADDRESSED_SERVICE/0J.1', 'offer_ref': offer['event_ref'],
            'authority_event': digest(event), 'source_sort': 'H', 'target_sort': 'A',
            'source_own_ref': digest(h), 'target_own_ref': digest(a),
            'artifact_sha256': offer['artifact_sha256'], 'rows': rows,
            'scope': 'EXACT_OFFER_SECTION_ONLY'}

def reduce_branch(c, catalog, selected, source_catalog, assets):
    require(type(selected) is list and len(set(selected)) == len(selected), 'DUPLICATE_SELECTION')
    require(all(i in catalog for i in selected), 'MISSING_EVENT')
    events = {i: catalog[i] for i in selected}; byref = {digest(e): e for e in events.values()}
    require(len(byref) == len(events), 'DUPLICATE_EVENT')
    trusted_roots = set(c['roots'].values()) | {c['covenant']}
    children = {}; dependencies = {}
    for key, e in events.items():
        require(type(e) is dict and set(e) == FIELDS and type(e['id']) is str and
                e['id'] == key and key.startswith('J_') and e['kind'] in OWNERS, 'EVENT_SCHEMA')
        b = OWNERS[e['kind']]; p = e['payload']; ref = digest(e)
        require(e['actor'] == b and e['source'] == b, 'ACTOR_SOURCE')
        require(e['origin'] == 'AUTHORED PREMISE' and e['selection'] == 'EXPLICIT_INPUT', 'AUTOMATIC_OR_UNRESOLVED_INPUT')
        require(ref in source_catalog[b] and ref not in source_catalog['H' if b == 'A' else 'A'], 'MISSING_OWN_INPUT')
        require(type(p) is dict and set(p) == BODY[e['kind']], 'PAYLOAD_SCHEMA')
        require(e['covenant_ref'] == c['covenant'], 'COVENANT_REPLACED')
        parent = e['own_parent']
        require(parent == c['roots'][b] or (parent in byref and byref[parent]['source'] == b), 'OWN_PARENT')
        require((b, parent) not in children, 'OWN_FORK'); children[b, parent] = ref
        wanted = {parent, c['covenant']}
        if b == 'A':
            require(p['offer_ref'] in byref and byref[p['offer_ref']]['kind'] == 'H_SERVICE_OFFER', 'MISSING_OR_WRONG_OFFER')
            wanted.add(p['offer_ref'])
        require(type(e['parents']) is list and e['parents'] == sorted(wanted), 'CAUSAL_PARENTS')
        dependencies[ref] = set(e['parents']) - trusted_roots
    pending = dict(byref); done = set(); order = []
    while pending:
        ready = sorted(k for k in pending if dependencies[k] <= done)
        require(bool(ready), 'CAUSAL_CYCLE_OR_MISSING')
        for ref in ready:
            order.append(ref); done.add(ref); del pending[ref]
    state = {'own_heads': deepcopy(c['roots']), 'new_own_histories': {'A': [], 'H': []},
             'offers': {}, 'decisions': {}, 'receiving_relations': {}, 'public_world': {},
             'covenant_ref': c['covenant'], 'base_world_ref': digest(c['world']),
             'old_Psi_ref': digest(c['world']['Psi']), 'A_response': 'NOT_RECORDED'}
    for ref in order:
        e = byref[ref]; b = e['actor']; p = e['payload']
        require(state['own_heads'][b] == e['own_parent'], 'STALE_OWN_PARENT')
        if e['kind'] == 'H_SERVICE_OFFER':
            state['offers'][ref] = service(c, e, assets)
        elif b == 'A':
            offer = state['offers'].get(p['offer_ref'])
            require(offer is not None and p['offer_ref'] not in state['decisions'], 'OFFER_ALREADY_DECIDED')
            if e['kind'] == 'A_ACCEPTS_SERVICE':
                state['receiving_relations'][p['offer_ref']] = receiving(c, offer, e)
                state['decisions'][p['offer_ref']] = {'event_ref': ref, 'kind': 'RECEIVE'}
            else:
                state['decisions'][p['offer_ref']] = {'event_ref': ref, 'kind': 'DECLINE_NO_MORAL_RANK'}
        else:
            r = resource(assets, p['artifact'], 'PUBLIC_DECLARATION')
            require(p['artifact_sha256'] == r['sha256'] and p['audience'] == 'WORLD' and
                    p['scope'] == 'WHOLE_PUBLIC_ARTIFACT_ONLY', 'DISCLOSURE_SCOPE')
            state['public_world'][ref] = {'source': 'H', 'artifact': p['artifact'],
                'path': r['path'], 'sha256': r['sha256'], 'bytes': r['bytes'],
                'scope': p['scope'], 'audience': 'WORLD', 'acceptance_required': False,
                'external_publication_performed': False}
        state['new_own_histories'][b].append(ref); state['own_heads'][b] = ref
    return state

def apply_service(state, offer_ref, artifact_sha256, h_state):
    """A type/term query, not delivery, consent, an actor event, or new emotion."""
    r = state['receiving_relations'].get(offer_ref)
    if r is None:
        return {'status': 'BLOCKED', 'reason': 'NO_RECIPIENT_ACCEPTANCE'}
    if r['artifact_sha256'] != artifact_sha256:
        return {'status': 'BLOCKED', 'reason': 'FOREIGN_SERVICE_PACKET'}
    rows = [x for x in r['rows'] if x['H_state'] == h_state]
    if len(rows) != 1:
        return {'status': 'BLOCKED', 'reason': 'OUTSIDE_OFFERED_SECTION'}
    return {'status': 'WELL_TYPED_DERIVATION_NOT_ACTION', 'source_sort': 'H',
            'target_sort': 'A', 'A_state': deepcopy(rows[0]['A_state']),
            'authority_event': r['authority_event']}

def replay(bundle, assets, witness, genesis):
    require(set(bundle) == {'schema', 'events', 'source_catalog', 'branches', 'main_branch'} and
            bundle['schema'] == SEM and set(bundle['source_catalog']) == {'A', 'H'}, 'INPUT_SCHEMA')
    c = context(witness, genesis); states = {}
    for name, selected in sorted(bundle['branches'].items()):
        states[name] = reduce_branch(c, bundle['events'], selected, bundle['source_catalog'], assets)
    offer = digest(bundle['events']['J_H_OFFER_1'])
    packet = assets['service_trace']['sha256']; point = c['world']['actors']['H']['point']
    queries = {name: apply_service(s, offer, packet, point) for name, s in states.items()}
    return {'schema': SEM, 'release_version': '0.3.0', 'base_witness_sha256': BASE_SHA,
            'historical_scope': 'English reconstruction of v0.5 a_h_lineage final; no additional actor input',
            'main_branch': bundle['main_branch'], 'roots': c['roots'], 'covenant_ref': c['covenant'],
            'event_refs': {k: digest(v) for k, v in sorted(bundle['events'].items())},
            'branches': states, 'application_queries': queries,
            'formal_novelty_against_E0plus': 'FAIL', 'limits': c['limits'],
            'source_tier': 'AUTHORED PREMISE / STRUCTURALLY VERIFIED',
            'phenomenology_measured': False, 'external_actor_authentication': 'NOT_PROVEN',
            'A_response': 'NOT_IMPLEMENTED_NOT_RECORDED', 'X': 'OPEN_HYPOTHESIS'}

if __name__ == '__main__':
    try:
        emit(replay(*inputs()))
    except Exception as exc:
        emit({'status': 'FAIL', 'reason': str(exc)}); raise SystemExit(1)
