from app.discovery.evidence import evidence_classify


def test_explicit_rfq_with_quantity_is_active_demand():
    r=evidence_classify('RFQ: We need 500 tons cement for Herat. Contact buyer@example.com', requested_product='cement', extracted={'quantities':[{'value':500,'unit':'ton'}], 'contacts':{'emails':['buyer@example.com']}, 'prices':[]})
    assert r['classification']=='Active Purchase Demand'
    assert r['evidence']['explicit_rfq'] is True
    assert r['demand_likelihood'] > 0.6


def test_directory_is_not_buyer_by_keywords_alone():
    r=evidence_classify('ABC Trading company profile and business directory listing', requested_product='cement', extracted={'contacts':{'emails':[],'phones':[]},'quantities':[],'prices':[]})
    assert r['classification']=='Directory/Company Profile'


def test_expired_request_is_not_active():
    r=evidence_classify('Expired RFQ: request to buy 100 tons cement', requested_product='cement', extracted={'quantities':[{'value':100,'unit':'ton'}], 'contacts':{'emails':[],'phones':[]}, 'prices':[]})
    assert r['classification']=='Expired/Closed Signal'
    assert r['demand_likelihood'] < 0.3


def test_supply_signal_separated_from_demand():
    r=evidence_classify('Manufacturer: we supply cement, available for export', requested_product='cement', extracted={'quantities':[],'prices':[],'contacts':{'emails':[],'phones':[]}})
    assert r['classification']=='Supply Signal'
