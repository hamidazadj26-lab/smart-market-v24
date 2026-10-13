from app.services.data_quality import _entity_quality

def test_entity_quality_missing_required():
    class X: name='A'; country='Iran'; phone=None
    r=_entity_quality(X(), ['name','country'], ['phone'])
    assert r['status']=='Needs Review'
    assert r['missing']==[]
    assert r['recommended_missing']==['phone']

def test_entity_quality_missing_entity():
    r=_entity_quality(None, ['name'], ['phone'])
    assert r['status']=='Missing'
    assert r['score']==0
