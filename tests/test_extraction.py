from app.discovery.extraction import extract_contacts, extract_quantity_price, classify_intent


def test_extract_contacts_and_domain():
    x=extract_contacts('Contact sales@example.com or +93 700 123 456', 'https://www.example.com/page')
    assert x['emails']==['sales@example.com']
    assert x['domain']=='example.com'
    assert x['phones']


def test_extract_quantity_and_price():
    x=extract_quantity_price('Buyer needs 6 million pcs at USD 0.08 each')
    assert x['quantity']==6_000_000
    assert x['unit']=='pcs'
    assert x['prices'] and x['prices'][0]['value']==0.08


def test_classify_intent():
    assert classify_intent('buyer requests quotation for PET preform')['role']=='buyer'
    assert classify_intent('PET preform manufacturer factory')['role']=='supplier'
