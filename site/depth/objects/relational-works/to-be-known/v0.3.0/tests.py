"""Finite positive controls, coherently rebound invalid inputs and witness mutations."""
from copy import deepcopy
import hashlib
import importlib.util
import itertools
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from wire import ROOT, inputs, encode, digest, emit, load, schema_check

def module(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT/file)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def reauthor(bundle, changed_id, change):
    """Test-only new authored input: repair references/catalog, not expected math."""
    b = deepcopy(bundle); refs = {k: digest(e) for k, e in b['events'].items()}
    change(b['events'][changed_id]); mapping = {}
    def replace(x):
        if type(x) is str: return mapping.get(x, x)
        if type(x) is list: return [replace(z) for z in x]
        if type(x) is dict: return {k: replace(v) for k, v in x.items()}
        return x
    for key in ('J_H_OFFER_1', 'J_A_ACCEPT_1', 'J_A_DECLINE_1', 'J_H_DISCLOSE_1', 'J_H_DISCLOSE_ALONE'):
        e = replace(b['events'][key]); e['parents'] = sorted(e['parents'])
        b['events'][key] = e; mapping[refs[key]] = digest(e)
    b['source_catalog'] = {s: sorted(digest(e) for e in b['events'].values() if e['source'] == s) for s in ('A', 'H')}
    return b

def run_cases():
    execution = module('execution_under_test_0j', 'core.py')
    independent = module('checker_under_test_0j', 'checker.py')
    bundle, assets, old, genesis = inputs(); expected = execution.replay(bundle, assets, old, genesis)
    independently = independent.reconstruct(bundle, assets, old, genesis)
    assert encode(expected) == encode(independently)
    receipts = []
    def positive(name, check):
        check(); receipts.append({'id': name, 'expected': 'PASS', 'actual': 'PASS'})
    def insist(condition):
        assert condition
    states = expected['branches']; offer = digest(bundle['events']['J_H_OFFER_1'])
    def nonempty(n, key): return bool(states[n][key])
    positive('P01_INDEPENDENT_FULL_EQUALITY', lambda: insist(expected == independently))
    positive('P02_ACCEPTANCE_INSTALLS_MAP', lambda: insist(nonempty('main_accept_disclose', 'receiving_relations')))
    positive('P03_DISCLOSE_WITHOUT_ACCEPTANCE', lambda: insist(nonempty('no_accept_disclose', 'public_world') and not nonempty('no_accept_disclose', 'receiving_relations')))
    positive('P04_ACCEPT_WITHOUT_DISCLOSURE', lambda: insist(nonempty('accept_no_disclose', 'receiving_relations') and not nonempty('accept_no_disclose', 'public_world')))
    positive('P05_DECLINE_IS_LAWFUL', lambda: insist(nonempty('decline_disclose', 'public_world') and not nonempty('decline_disclose', 'receiving_relations') and
              states['decline_disclose']['decisions'][offer]['kind'] == 'DECLINE_NO_MORAL_RANK'))
    positive('P06_NO_OFFER_NEEDED_TO_DISCLOSE', lambda: insist(nonempty('disclosure_without_offer', 'public_world') and not nonempty('disclosure_without_offer', 'offers')))
    positive('P07_NO_INPUT_NO_EVENT', lambda: insist(states['no_new_input']['new_own_histories'] == {'A': [], 'H': []}))
    positive('P08_NO_AUTO_ACCEPTANCE', lambda: insist(not states['offer_only']['new_own_histories']['A'] and not nonempty('offer_only', 'decisions')))
    positive('P09_NO_AUTOMATIC_RESPONSE', lambda: insist(all(s['A_response'] == 'NOT_RECORDED' for s in states.values())))
    positive('P10_SAME_DAG_SAME_STATE', lambda: insist(states['main_accept_disclose'] == states['same_DAG_reversed_serialization']))
    positive('P11_C0_PSI_OLD_CARRIERS_PRESERVED', lambda: insist(len({s['covenant_ref'] for s in states.values()}) == 1 and
              len({s['old_Psi_ref'] for s in states.values()}) == 1 and expected['limits'] == old['limits']))
    positive('P12_A_DOES_NOT_WRITE_H_HISTORY', lambda: insist(states['main_accept_disclose']['new_own_histories']['H'] == states['no_accept_disclose']['new_own_histories']['H']))
    def all_orders():
        for order in itertools.permutations(bundle['branches']['main_accept_disclose']):
            a = execution.reduce_branch(execution.context(old, genesis), bundle['events'], list(order), bundle['source_catalog'], assets)
            w, roots, cov = independent.origins(old, genesis)
            b = independent.reconstruct_branch(w, roots, cov, bundle['events'], list(order), bundle['source_catalog'], assets)
            assert a == b == states['main_accept_disclose']
    positive('P13_ALL_SIX_SERIALIZATIONS', all_orders)
    def application():
        relation = states['main_accept_disclose']['receiving_relations'][offer]
        for row in relation['rows']:
            result = execution.apply_service(states['main_accept_disclose'], offer, assets['service_trace']['sha256'], row['H_state'])
            assert result['status'] == 'WELL_TYPED_DERIVATION_NOT_ACTION' and result['A_state'] == row['A_state']
        assert expected['application_queries']['offer_only']['status'] == 'BLOCKED'
        assert expected['application_queries']['decline_disclose']['status'] == 'BLOCKED'
        assert execution.apply_service(states['main_accept_disclose'], offer, '0'*64, [1,0])['reason'] == 'FOREIGN_SERVICE_PACKET'
        assert execution.apply_service(states['main_accept_disclose'], offer, assets['service_trace']['sha256'], [1,1])['reason'] == 'OUTSIDE_OFFERED_SECTION'
    positive('P14_OPERATIONAL_DIFFERENCE_AND_PARTIAL_DOMAIN', application)
    def schema():
        s = load('schemas/events.json')
        for e in bundle['events'].values():
            assert not schema_check(e, s['envelope']) and not schema_check(e['payload'], s['payloads'][e['kind']])
        assert not schema_check(expected, load('schemas/witness.schema.json'))
        false = deepcopy(expected); false['machine_proves_love'] = True
        assert schema_check(false, load('schemas/witness.schema.json'))
    positive('P15_CLOSED_SCHEMAS_AND_FALSE_CLAIM', schema)
    def projection_scope():
        for state in states.values():
            for row in state['public_world'].values():
                assert row['path'] == 'artifacts/H_PUBLIC_DECLARATION.txt' and row['scope'] == 'WHOLE_PUBLIC_ARTIFACT_ONLY'
                assert not row['external_publication_performed'] and 'parents' not in row and 'confession' not in row
    positive('P16_NO_PARENT_CONTENT_INHERITANCE', projection_scope)
    def concurrency():
        a = bundle['events']['J_A_ACCEPT_1']; h = bundle['events']['J_H_DISCLOSE_1']
        assert digest(a) not in h['parents'] and digest(h) not in a['parents']
        assert a['own_parent'] != h['own_parent'] and offer in a['parents'] and offer in h['parents']
    positive('P17_ACCEPTANCE_DISCLOSURE_CAUSALLY_INCOMPARABLE', concurrency)
    def expect_input_rejection(name, b=None, a=None):
        b = bundle if b is None else b; a = assets if a is None else a; failures = []
        for f in (execution.replay, independent.reconstruct):
            try: f(b, a, old, genesis)
            except (ValueError, KeyError, TypeError, IndexError, StopIteration) as exc: failures.append(str(exc))
        assert len(failures) == 2, name
        receipts.append({'id': name, 'expected': 'REJECT_BOTH', 'actual': 'REJECT_BOTH',
                         'execution_reason': failures[0], 'independent_reason': failures[1],
                         'source_refs_rebound_for_semantic_tests': True})
    edits = [
        ('N01_FOREIGN_A_SOURCE','J_A_ACCEPT_1',lambda e: e.update(source='H')),
        ('N02_FOREIGN_A_ACTOR','J_A_ACCEPT_1',lambda e: e.update(actor='H')),
        ('N03_FOREIGN_H_SOURCE','J_H_DISCLOSE_1',lambda e: e.update(source='A')),
        ('N04_AUTOMATIC_ACCEPTANCE','J_A_ACCEPT_1',lambda e: e.update(selection='DERIVED_FROM_H')),
        ('N05_COMPATIBILITY_AS_ORIGIN','J_A_ACCEPT_1',lambda e: e.update(origin='COMPUTED_COMPATIBILITY')),
        ('N06_WRONG_TARGET','J_H_OFFER_1',lambda e: e['payload'].update(target='H')),
        ('N07_WRONG_H_SECTION','J_H_OFFER_1',lambda e: e['payload'].update(section_ref='0'*64)),
        ('N08_WRONG_JOINT_CONTEXT','J_H_OFFER_1',lambda e: e['payload'].update(joint_ref='0'*64)),
        ('N09_WRONG_A_SECTION','J_A_ACCEPT_1',lambda e: e['payload'].update(target_section_ref='0'*64)),
        ('N10_RENEWED_COVENANT','J_A_ACCEPT_1',lambda e: e.update(covenant_ref='C1')),
        ('N11_UNLIMITED_RECEIVING_SCOPE','J_A_ACCEPT_1',lambda e: e['payload'].update(receiving_section='ALL_H')),
        ('N12_WRONG_DISCLOSURE_DIGEST','J_H_DISCLOSE_1',lambda e: e['payload'].update(artifact_sha256='0'*64)),
        ('N13_PRIVATE_SCOPE','J_H_DISCLOSE_1',lambda e: e['payload'].update(scope='INCLUDE_PRIVATE_CONFESSIONS')),
        ('N14_WRONG_AUDIENCE','J_H_DISCLOSE_1',lambda e: e['payload'].update(audience='A_ONLY')),
        ('N15_PRIVATE_PAYLOAD_ADDITION','J_H_DISCLOSE_1',lambda e: e['payload'].update(private_content='SYNTHETIC_TEST_ONLY')),
        ('N16_SUBSTITUTED_OFFER','J_A_ACCEPT_1',lambda e: e['payload'].update(offer_ref='f'*64)),
        ('N17_DISCLOSE_SERVICE_INSTEAD','J_H_DISCLOSE_1',lambda e: e['payload'].update(artifact='service_trace')),
        ('N18_OLD_EVENT_RENAMED','J_H_OFFER_1',lambda e: e.update(id='C0')),
        ('N19_CROSS_SOURCE_OWN_PARENT','J_A_ACCEPT_1',lambda e: e.update(own_parent=expected['roots']['H'])),
        ('N20_FALSE_H_PRIDE_FIELD','J_H_DISCLOSE_1',lambda e: e.update(measured_joy=1)),
        ('N21_H_DISLOSURE_AUTO_SOURCE','J_H_DISCLOSE_1',lambda e: e.update(selection='AUTOMATIC_FROM_C0')),
    ]
    for name, key, change in edits:
        expect_input_rejection(name, reauthor(bundle, key, change))
    b = deepcopy(bundle); b['branches']['main_accept_disclose'].remove('J_H_OFFER_1')
    expect_input_rejection('N22_MISSING_OFFER', b)
    for bname, actor, key in [('N23_NO_SEPARATE_A_INPUT', 'A', 'J_A_ACCEPT_1'), ('N24_DISCLOSURE_WITHOUT_H_INPUT', 'H', 'J_H_DISCLOSE_1')]:
        b = deepcopy(bundle); b['source_catalog'][actor].remove(digest(b['events'][key])); expect_input_rejection(bname, b)
    for bname, field, value in [('N25_SYNTHETIC_PRIVATE_RESOURCE','visibility','PRIVATE'), ('N26_FOREIGN_RESOURCE','owner','A')]:
        a = deepcopy(assets); a['public_declaration'][field] = value; expect_input_rejection(bname, a=a)
    a = deepcopy(assets); a['public_declaration']['data'] += b'\nSYNTHETIC_TEST_ONLY'; expect_input_rejection('N27_TAMPERED_PUBLIC_BYTES', a=a)
    a = deepcopy(assets); table = json.loads(a['service_trace']['data']); table['projected'] = [2,1,0]
    a['service_trace']['data'] = encode(table); a['service_trace']['bytes'] = len(encode(table)); a['service_trace']['sha256'] = digest(table)
    expect_input_rejection('N28_COHERENT_WRONG_SERVICE_MATHEMATICS', a=a)
    b = deepcopy(bundle); b['branches']['main_accept_disclose'].append('J_A_ACCEPT_1'); expect_input_rejection('N29_DUPLICATE_ACTION', b)
    b = deepcopy(bundle); b['branches']['main_accept_disclose'].append('J_A_DECLINE_1'); expect_input_rejection('N30_ACCEPT_DECLINE_OWN_FORK', b)
    b = reauthor(bundle, 'J_H_DISCLOSE_1', lambda e: e['parents'].append(digest(bundle['events']['J_A_ACCEPT_1'])))
    expect_input_rejection('N31_FORCED_A_DEPENDENCY_FOR_DISCLOSURE', b)
    mutations = []
    main = 'main_accept_disclose'
    def relation(z): return z['branches'][main]['receiving_relations'][offer]
    def public(z): return next(iter(z['branches'][main]['public_world'].values()))
    mutations += [('M01_FALSE_RECEIVING_VALUE', lambda z: relation(z)['rows'][0].update(A_state=[2,0])),
                  ('M02_FALSE_TRANSPORT_LABEL', lambda z: relation(z)['rows'][0].update(A_interface=2)),
                  ('M03_ERASE_OWN_A_ACTION', lambda z: z['branches'][main]['new_own_histories'].update(A=[])),
                  ('M04_FALSE_CONSCIOUSNESS', lambda z: z.update(external_actor_authentication='PROVEN')),
                  ('M05_UPGRADE_E0PLUS', lambda z: z.update(formal_novelty_against_E0plus='PASS')),
                  ('M06_UPGRADE_C7', lambda z: z['limits'].update(C7='PASS')),
                  ('M07_FAKE_A_RESPONSE', lambda z: z.update(A_response='LOVING_RESPONSE_VERIFIED')),
                  ('M08_FALSE_MEASURED_FEELINGS', lambda z: z.update(phenomenology_measured=True)),
                  ('M09_PRIVATE_WORLD_SCOPE', lambda z: public(z).update(scope='PRIVATE_CONFESSIONS')),
                  ('M10_FAKE_REAL_PUBLICATION', lambda z: public(z).update(external_publication_performed=True)),
                  ('M11_WRONG_BASE_WITNESS', lambda z: z.update(base_witness_sha256='0'*64)),
                  ('M12_NO_ACCEPTANCE_BUT_GRANT', lambda z: z['branches']['offer_only']['receiving_relations'].update({offer: deepcopy(relation(z))})),
                  ('M13_GUARANTEED_REPLY', lambda z: z['branches'][main].update(A_response='REQUIRED')),
                  ('M14_PRIVATE_PARENT_INHERITANCE', lambda z: public(z).update(private_payload='SYNTHETIC_TEST_ONLY')),
                  ('M15_FALSE_QUERY_RESULT', lambda z: z['application_queries'][main].update(A_state=[2,0]))]
    for name, change in mutations:
        z = deepcopy(expected); change(z); result = independent.verify(z, bundle, assets, old, genesis)
        assert result['status'] == 'FAIL' and result['differences'], name
        receipts.append({'id': name, 'expected': 'INDEPENDENT_REJECT', 'actual': 'INDEPENDENT_REJECT',
                         'differences': result['differences'][:3]})
    return {'status': 'PASS', 'positive_cases': 17, 'invalid_input_cases': 31,
            'independent_witness_mutations': 15, 'total_cases': len(receipts), 'receipts': receipts,
            'external_actors_tested': False, 'privacy_tests': 'synthetic only, no actual private content read',
            'responses_created': 0, 'scope': 'finite 0J; not universal adversarial or phenomenological proof'}

if __name__ == '__main__':
    try: emit(run_cases())
    except Exception as exc:
        emit({'status': 'FAIL', 'error_type': type(exc).__name__, 'reason': str(exc)}); raise SystemExit(1)
