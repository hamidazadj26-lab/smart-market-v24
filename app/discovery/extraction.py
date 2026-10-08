from __future__ import annotations
import re
from urllib.parse import urlparse
from .normalization import normalize_digits, parse_number, canonical_currency, canonical_unit, extract_quantities, extract_prices


def clean_text(value: str | None) -> str:
    return ' '.join((value or '').replace('ي','ی').replace('ك','ک').split())


def extract_contacts(text: str, url: str | None = None) -> dict:
    t = clean_text(text)
    emails = sorted(set(re.findall(r'\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b', t, re.I)))[:10]
    phones = sorted(set(re.findall(r'(?<!\d)(?:\+?\d[\d\s().-]{7,}\d)(?!\d)', t)))[:10]
    domain = None
    if url:
        try:
            host = urlparse(url).netloc.lower().split('@')[-1].split(':')[0]
            domain = host[4:] if host.startswith('www.') else host
        except ValueError:
            pass
    return {'emails': emails, 'phones': phones, 'domain': domain}


def extract_quantity_price(text: str) -> dict:
    quantities = extract_quantities(text)
    prices = extract_prices(text)
    first = quantities[0] if quantities else {}
    return {
        'quantity': first.get('value'),
        'unit': first.get('unit'),
        'prices': [
            {'value': p['value'], 'currency': p['currency'], 'unit': p.get('unit'), 'raw': p['raw']}
            for p in prices
        ],
        'quantities': quantities,
    }


def classify_intent(text: str) -> dict:
    low = clean_text(text).lower()
    demand_words = ('buy','purchase','procurement','rfq','request for quotation','wanted','need','import','buyer','خرید','درخواست خرید','نیاز','استعلام','مناقصه','خریدار')
    supplier_words = ('manufacturer','factory','producer','supplier','exporter','production','تولیدکننده','کارخانه','تولید','فروشنده','تأمین کننده','تامین کننده','صادرکننده')
    distributor_words = ('distributor','dealer','wholesaler','trading','importer','واردات','توزیع','بازرگانی','نماینده')
    d=[w for w in demand_words if w in low]; s=[w for w in supplier_words if w in low]; r=[w for w in distributor_words if w in low]
    if d: role='buyer'
    elif s: role='supplier'
    elif r: role='distributor_or_importer'
    else: role='unknown'
    return {'role':role,'demand_keywords':d[:10],'supplier_keywords':s[:10],'distributor_keywords':r[:10]}
