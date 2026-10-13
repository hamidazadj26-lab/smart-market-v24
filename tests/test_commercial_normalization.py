from app.discovery.normalization import normalize_commercial_text, extract_quantities, extract_prices, parse_number


def test_number_formats():
    assert parse_number('1,250.50') == 1250.50
    assert parse_number('1.250,50') == 1250.50
    assert parse_number('۱۲۵۰') == 1250


def test_quantity_normalization_multilingual():
    q=extract_quantities('درخواست خرید 1,250 تن و 2.5 million pieces')
    assert q[0]['value']==1250 and q[0]['unit']=='ton'
    assert any(x['value']==2_500_000 and x['unit']=='pcs' for x in q)


def test_price_currency_and_basis():
    p=extract_prices('$1,200/ton and 45000 افغانی')
    assert p[0]['currency']=='USD' and p[0]['value']==1200 and p[0]['unit']=='ton'
    assert any(x['currency']=='AFN' and x['value']==45000 for x in p)


def test_commercial_payload_preserves_raw_evidence():
    payload=normalize_commercial_text('Buyer needs 500 kg at USD 2.40/kg. Contact sales@example.com', source_url='https://example.com/rfq', source_title='RFQ')
    assert payload['raw_text'].startswith('Buyer needs')
    assert payload['prices'][0]['currency']=='USD'
    assert payload['quantities'][0]['unit']=='kg'
    assert payload['contacts']['emails']==['sales@example.com']
    assert payload['evidence_spans']
