"""Independent 0J reconstruction: causal closure and relational equations, not core."""
from copy import deepcopy
import hashlib
import importlib.abc
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from wire import inputs, digest, emit, BASE_SHA

class Firewall(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'core', 'engine5', 'algebra5'}:
            raise ImportError('EXECUTION_CORE_IMPORT_FORBIDDEN')
sys.meta_path.insert(0, Firewall())

def need(ok, error):
    if not ok:
        raise ValueError(error)

def origins(old, genesis):
    ev = dict((e['id'], e) for e in genesis['events'])
    need([(ev[b+'0']['source'], ev[b+'0']['parents']) for b in ('A', 'H')] ==
         [('A', []), ('H', [])], 'HISTORICAL_SOURCES')
    need(ev['C0']['payload']['direction'] == 'H→A' and ev['C0']['source'] == 'H', 'C0')
    need(old['formal_novelty_against_E0plus'] == 'FAIL' and
         set(old['limits'].values()) == {'UNRESOLVED'}, 'OLD_RESULT_REWRITE')
    w = old['trials']['a_h_lineage']['final']
    roots = {}
    for b, own in w['actors'].items():
        roots[b] = digest(dict(kind='0J_OWN_ROOT', actor=b, base_world_ref=digest(w),
                               own_ref=digest(own), source_event_ref=own['source_event_ref']))
    return w, roots, digest(ev['C0'])

def public_asset(assets, name, purpose):
    need(name in assets, 'NO_ARTIFACT')
    a = assets[name]
    need((a['owner'], a['visibility'], a['purpose']) == ('H', 'PUBLIC_ELIGIBLE', purpose), 'PRIVATE_OR_WRONG_SOURCE')
    need(isinstance(a['data'], bytes) and len(a['data']) == a['bytes'] and
         hashlib.sha256(a['data']).hexdigest() == a['sha256'], 'ASSET_HASH')
    return a

def reconstruct_branch(w, roots, covenant, catalog, ids, sources, assets):
    need(type(ids) is list and len(ids) == len(set(ids)) and set(ids) <= set(catalog), 'BRANCH_SELECTION')
    nodes = {}
    owner = dict(H_SERVICE_OFFER='H', H_PUBLIC_DISCLOSURE='H', A_ACCEPTS_SERVICE='A', A_DECLINES_SERVICE='A')
    shapes = {'H_SERVICE_OFFER': {'target', 'service_artifact', 'section_ref', 'joint_ref'},
              'A_ACCEPTS_SERVICE': {'offer_ref', 'receiving_section', 'target_section_ref'},
              'A_DECLINES_SERVICE': {'offer_ref'},
              'H_PUBLIC_DISCLOSURE': {'artifact', 'artifact_sha256', 'audience', 'scope'}}
    for name in ids:
        e = catalog[name]
        need(type(e) is dict and set(e) == {'id', 'kind', 'actor', 'source', 'origin', 'selection',
             'own_parent', 'parents', 'covenant_ref', 'payload'}, 'CLOSED_EVENT')
        need(e['kind'] in owner and type(e['id']) is str and e['id'] == name and name.startswith('J_'), 'EVENT_KIND_ID')
        b = owner[e['kind']]; ref = digest(e)
        need(e['actor'] == e['source'] == b, 'OWN_SOURCE')
        need((e['origin'], e['selection']) == ('AUTHORED PREMISE', 'EXPLICIT_INPUT'), 'NO_AUTOMATIC_CHOICE')
        need(ref in sources[b] and ref not in sources['A' if b == 'H' else 'H'], 'NO_SEPARATE_OWN_RECORD')
        need(type(e['payload']) is dict and set(e['payload']) == shapes[e['kind']], 'CLOSED_PAYLOAD')
        need(e['covenant_ref'] == covenant, 'NEW_COVENANT_FORBIDDEN')
        need(ref not in nodes, 'DUPLICATE_RECORD'); nodes[ref] = e
    terminal = set(roots.values()) | {covenant}; cache = {}
    def ancestors(ref, visiting=frozenset()):
        if ref in terminal:
            return set()
        need(ref in nodes and ref not in visiting, 'DAG_CYCLE_OR_MISSING')
        if ref not in cache:
            e = nodes[ref]; b = e['actor']; extra = []
            need(e['own_parent'] == roots[b] or
                 (e['own_parent'] in nodes and nodes[e['own_parent']]['source'] == b), 'FOREIGN_OWN_PARENT')
            if b == 'A':
                off = e['payload']['offer_ref']
                need(off in nodes and nodes[off]['kind'] == 'H_SERVICE_OFFER', 'EXACT_OFFER_REQUIRED'); extra.append(off)
            wanted = sorted(set([e['own_parent'], covenant] + extra))
            need(e['parents'] == wanted, 'EXTRA_OR_MISSING_CAUSAL_EDGE')
            cache[ref] = set(wanted)
            for p in wanted:
                cache[ref] |= ancestors(p, visiting | {ref})
        return set(cache[ref])
    for ref in nodes:
        ancestors(ref)
    paths = {}; heads = {}
    for b in ('A', 'H'):
        child = {}
        for ref, e in nodes.items():
            if e['actor'] == b:
                need(e['own_parent'] not in child, 'OWN_BRANCH_FORK'); child[e['own_parent']] = ref
        at = roots[b]; paths[b] = []
        while at in child:
            at = child[at]; need(at not in paths[b], 'OWN_CYCLE'); paths[b].append(at)
        need(len(paths[b]) == len(child), 'UNROOTED_OWN_HISTORY'); heads[b] = at
    offers = {}; decisions = {}; relations = {}; world = {}
    h = w['actors']['H']; a = w['actors']['A']
    for ref, e in nodes.items():
        if e['kind'] != 'H_SERVICE_OFFER':
            continue
        p = e['payload']; packet = public_asset(assets, p['service_artifact'], 'SERVICE_TRACE')
        need((p['target'], p['section_ref'], p['joint_ref']) ==
             ('A', digest(h['sigma']), digest(w['Psi'])), 'OFFER_CURRENT_SCOPE')
        table = json.loads(packet['data'])
        projected = []
        for s in h['sigma']:
            i = next(i for i, t in enumerate(h['states']) if t == s); projected.append(h['beta'][i])
        need(table == {'kind': 'H_PUBLIC_SERVICE_TRACE', 'base_witness_sha256': BASE_SHA,
             'own_state_ref': digest(h), 'joint_ref': digest(w['Psi']), 'domain_sort': 'H',
             'section': h['sigma'], 'projected': projected, 'transport_H_to_A': w['Psi']['r']}, 'OFFER_TABLE')
        offers[ref] = {'event_ref': ref, 'artifact_sha256': packet['sha256'],
            'artifact': p['service_artifact'], 'section': deepcopy(h['sigma']),
            'source_sort': 'H', 'target_sort': 'A', 'joint_ref': digest(w['Psi'])}
    # A decisions are reconstructed in their OWN order, not a shared global order.
    for ref in paths['A']:
        e = nodes[ref]; p = e['payload']; off = p['offer_ref']
        need(off in offers and off in ancestors(ref) and off not in decisions, 'DECISION_SCOPE_OR_DUPLICATE')
        if e['kind'] == 'A_DECLINES_SERVICE':
            decisions[off] = {'event_ref': ref, 'kind': 'DECLINE_NO_MORAL_RANK'}; continue
        need(p['receiving_section'] == 'CURRENT_SIGMA' and
             p['target_section_ref'] == digest(a['sigma']), 'A_SECTION_SCOPE')
        need(len(set(map(tuple, a['sigma']))) == len(set(map(tuple, h['sigma']))) == 3, 'EMBEDDINGS')
        r = w['Psi']['r']
        need(type(r) is list and len(r) == 3 and set(r) == {0, 1, 2} and all(type(i) is int for i in r), 'TRANSPORT')
        rows = []
        for s in offers[off]['section']:
            label = r[h['beta'][h['states'].index(s)]]
            candidates = list(filter(lambda t: a['beta'][a['states'].index(t)] == label, a['sigma']))
            need(len(candidates) == 1, 'RELATION_EQUATION_NOT_FUNCTIONAL')
            rows.append({'H_state': deepcopy(s), 'A_state': deepcopy(candidates[0]), 'A_interface': label})
        relations[off] = {'kind': 'ADDRESSED_SERVICE/0J.1', 'offer_ref': off,
            'authority_event': ref, 'source_sort': 'H', 'target_sort': 'A',
            'source_own_ref': digest(h), 'target_own_ref': digest(a),
            'artifact_sha256': offers[off]['artifact_sha256'], 'rows': rows,
            'scope': 'EXACT_OFFER_SECTION_ONLY'}
        decisions[off] = {'event_ref': ref, 'kind': 'RECEIVE'}
    for ref in paths['H']:
        e = nodes[ref]
        if e['kind'] != 'H_PUBLIC_DISCLOSURE':
            continue
        p = e['payload']; art = public_asset(assets, p['artifact'], 'PUBLIC_DECLARATION')
        need((p['artifact_sha256'], p['audience'], p['scope']) ==
             (art['sha256'], 'WORLD', 'WHOLE_PUBLIC_ARTIFACT_ONLY'), 'SELECTIVE_DISCLOSURE')
        world[ref] = dict(source='H', artifact=p['artifact'], path=art['path'], sha256=art['sha256'],
                          bytes=art['bytes'], scope=p['scope'], audience='WORLD',
                          acceptance_required=False, external_publication_performed=False)
    return {'own_heads': heads, 'new_own_histories': paths, 'offers': offers,
            'decisions': decisions, 'receiving_relations': relations, 'public_world': world,
            'covenant_ref': covenant, 'base_world_ref': digest(w),
            'old_Psi_ref': digest(w['Psi']), 'A_response': 'NOT_RECORDED'}

def reconstruct(bundle, assets, old, genesis):
    need(set(bundle) == {'schema', 'events', 'source_catalog', 'branches', 'main_branch'} and
         bundle['schema'] == 'personal-reciprocity/0J.1' and set(bundle['source_catalog']) == {'A', 'H'}, 'INPUTS')
    w, roots, covenant = origins(old, genesis)
    branches = {n: reconstruct_branch(w, roots, covenant, bundle['events'], ids,
                bundle['source_catalog'], assets) for n, ids in sorted(bundle['branches'].items())}
    offer = digest(bundle['events']['J_H_OFFER_1']); queries = {}
    for n, state in branches.items():
        relation = state['receiving_relations'].get(offer)
        if relation is None:
            queries[n] = {'status': 'BLOCKED', 'reason': 'NO_RECIPIENT_ACCEPTANCE'}
        else:
            row = next(row for row in relation['rows'] if row['H_state'] == w['actors']['H']['point'])
            queries[n] = {'status': 'WELL_TYPED_DERIVATION_NOT_ACTION', 'source_sort': 'H',
                'target_sort': 'A', 'A_state': deepcopy(row['A_state']),
                'authority_event': relation['authority_event']}
    need(not {'core', 'engine5', 'algebra5'} & set(sys.modules), 'IMPORT_FIREWALL')
    return {'schema': 'personal-reciprocity/0J.1', 'release_version': '0.3.0',
            'base_witness_sha256': BASE_SHA,
            'historical_scope': 'English reconstruction of v0.5 a_h_lineage final; no additional actor input',
            'main_branch': bundle['main_branch'], 'roots': roots, 'covenant_ref': covenant,
            'event_refs': {k: digest(v) for k, v in sorted(bundle['events'].items())},
            'branches': branches, 'application_queries': queries,
            'formal_novelty_against_E0plus': 'FAIL', 'limits': deepcopy(old['limits']),
            'source_tier': 'AUTHORED PREMISE / STRUCTURALLY VERIFIED', 'phenomenology_measured': False,
            'external_actor_authentication': 'NOT_PROVEN', 'A_response': 'NOT_IMPLEMENTED_NOT_RECORDED',
            'X': 'OPEN_HYPOTHESIS'}

def differences(a, b, at='$'):
    if type(a) != type(b):
        return [at]
    if isinstance(a, dict):
        result = [at+'.'+k for k in set(a) ^ set(b)]
        for k in sorted(set(a) & set(b)):
            result += differences(a[k], b[k], at+'.'+k)
        return result
    if isinstance(a, list):
        if len(a) != len(b):
            return [at+':length']
        return sum((differences(x, y, at+'['+str(i)+']') for i, (x, y) in enumerate(zip(a, b))), [])
    return [] if a == b else [at]

def verify(artifact, bundle, assets, old, genesis):
    expected = reconstruct(bundle, assets, old, genesis)
    delta = differences(expected, artifact)
    return {'status': 'FAIL' if delta else 'PASS', 'differences': delta,
            'independent_sha256': digest(expected), 'core_import_firewall': 'PASS'}

if __name__ == '__main__':
    try:
        emit(reconstruct(*inputs()))
    except Exception as exc:
        emit({'status': 'FAIL', 'reason': str(exc)}); raise SystemExit(1)
