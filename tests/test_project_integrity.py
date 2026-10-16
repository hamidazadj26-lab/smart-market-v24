from pathlib import Path
import ast

ROOT=Path(__file__).resolve().parents[1]

def _revisions():
    rows={}
    for path in sorted((ROOT/'migrations/versions').glob('*.py')):
        tree=ast.parse(path.read_text())
        values={}
        for node in tree.body:
            if isinstance(node,ast.Assign):
                for target in node.targets:
                    if isinstance(target,ast.Name) and target.id in {'revision','down_revision'}:
                        values[target.id]=ast.literal_eval(node.value)
        rows[path.name]=(values['revision'],values['down_revision'])
    return rows

def test_migration_chain_is_single_and_complete():
    rows=_revisions()
    ids=[revision for revision,_ in rows.values()]
    assert len(ids)==len(set(ids))
    by_id={revision:down for revision,down in rows.values()}
    heads=[revision for revision in ids if revision not in set(by_id.values())]
    assert len(heads)==1
    assert heads[0]=='0043_nullable_derived_offer_totals'
    assert by_id['0043_nullable_derived_offer_totals']=='0042_entity_identity_integrity'
    assert by_id['0011_opportunity_operating_system']=='0010_market_price_intelligence'

def test_production_auth_has_no_passlib_dependency():
    req=(ROOT/'requirements.txt').read_text().lower()
    auth=(ROOT/'app/security/auth.py').read_text().lower()
    assert 'passlib' not in req
    assert 'argon2' in req
    assert 'argon2' in auth

def test_pytest_is_self_contained():
    assert 'pythonpath = .' in (ROOT/'pytest.ini').read_text()

def test_entity_integrity_constraints_are_declared():
    models=(ROOT/'app/models/models.py').read_text()
    migration=(ROOT/'migrations/versions/0042_entity_identity_integrity.py').read_text()
    assert 'ux_entity_identities_natural_key' in models
    assert 'ck_entity_identities_confidence_range' in models
    assert 'ck_entity_links_not_self' in models
    assert 'duplicate natural keys exist' in migration
    assert 'self-links exist' in migration
