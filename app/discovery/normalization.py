from __future__ import annotations
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse

DIGIT_MAP = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789')
CURRENCY_ALIASES = {
    '$':'USD','usd':'USD','us$':'USD','dollar':'USD','dollars':'USD','دلار':'USD',
    'afn':'AFN','afghani':'AFN','afghanis':'AFN','افغانی':'AFN',
    'irr':'IRR','rial':'IRR','ریال':'IRR', 'تومان':'IRR',
    'eur':'EUR','€':'EUR','euro':'EUR','یورو':'EUR',
}
UNIT_ALIASES = {
    'kg':'kg','kgs':'kg','kilogram':'kg','kilograms':'kg','کیلو':'kg','کیلوگرم':'kg',
    'g':'g','gram':'g','grams':'g','گرم':'g',
    'ton':'ton','tons':'ton','tonne':'ton','tonnes':'ton','mt':'ton','metric ton':'ton','تن':'ton',
    'liter':'liter','litre':'liter','liters':'liter','litres':'liter','l':'liter','لیتر':'liter',
    'meter':'meter','meters':'meter','m':'meter','متر':'meter',
    'pcs':'pcs','pc':'pcs','piece':'pcs','pieces':'pcs','عدد':'pcs','قطعه':'pcs',
    'set':'set','sets':'set','دستگاه':'set','ست':'set',
    'box':'box','boxes':'box','کارتن':'box','carton':'box',
}


def normalize_digits(text: str | None) -> str:
    return (text or '').translate(DIGIT_MAP).replace('\u066c', ',').replace('\u066b', '.')


def clean_text(text: str | None) -> str:
    return ' '.join(normalize_digits(text).replace('ي','ی').replace('ك','ک').split())


def parse_number(raw: str) -> float | None:
    s = normalize_digits(raw).strip().replace(' ', '')
    if not s: return None
    # 1.234,56 -> 1234.56; 1,234.56 -> 1234.56; 1,234 -> 1234
    if ',' in s and '.' in s:
        if s.rfind(',') > s.rfind('.'): s = s.replace('.', '').replace(',', '.')
        else: s = s.replace(',', '')
    elif ',' in s:
        parts=s.split(',')
        s=''.join(parts) if len(parts[-1])==3 else s.replace(',', '.')
    elif s.count('.')>1:
        s=s.replace('.','')
    try: return float(Decimal(s))
    except (InvalidOperation, ValueError): return None


def canonical_currency(raw: str | None) -> str | None:
    if not raw: return None
    key=raw.strip().lower()
    return CURRENCY_ALIASES.get(key, key.upper() if len(key)<=5 else None)


def canonical_unit(raw: str | None) -> str | None:
    if not raw: return None
    return UNIT_ALIASES.get(raw.strip().lower())


def extract_quantities(text: str) -> list[dict]:
    t=clean_text(text); out=[]
    unit_pattern=r'(million|میلیون|billion|میلیارد|thousand|هزار|kg|kgs|kilograms?|کیلوگرم|g|grams?|گرم|mt|metric\s+tons?|tonnes?|tons?|تن|liters?|litres?|l|لیتر|meters?|m|متر|pcs?|pieces?|عدد|قطعه|sets?|ست|دستگاه|boxes?|box|کارتن)'
    for m in re.finditer(r'(?<!\w)([0-9][0-9,\.\s]*)\s*'+unit_pattern+r'\b', t, re.I):
        value=parse_number(m.group(1)); unit=m.group(2).lower()
        if value is None: continue
        multiplier=1.0
        if unit in ('million','میلیون'): value*=1_000_000; unit='pcs'
        elif unit in ('billion','میلیارد'): value*=1_000_000_000; unit='pcs'
        elif unit in ('thousand','هزار'): value*=1000; unit='pcs'
        unit=canonical_unit(unit) or unit
        out.append({'value':value,'unit':unit,'raw':m.group(0),'start':m.start(),'end':m.end()})
    return out[:20]


def extract_prices(text: str) -> list[dict]:
    t=clean_text(text); out=[]
    currency=r'(USD|US\$|\$|AFN|IRR|EUR|€|دلار|افغانی|ریال|تومان)'
    patterns=[
        rf'(?P<currency>{currency})\s*(?P<value>[0-9][0-9,\.\s]*)',
        rf'(?P<value>[0-9][0-9,\.\s]*)\s*(?P<currency>{currency})',
    ]
    for pattern in patterns:
        for m in re.finditer(pattern,t,re.I):
            value=parse_number(m.group('value')); cur=canonical_currency(m.group('currency'))
            if value is None or not cur: continue
            # Capture a nearby pricing basis without pretending it is known when absent.
            tail=t[m.end():m.end()+30]
            um=re.match(r'\s*(?:/|per|به ازای هر)?\s*(kg|ton|mt|pcs?|piece|عدد|کیلوگرم|تن)',tail,re.I)
            basis=canonical_unit(um.group(1)) if um else None
            out.append({'value':value,'currency':cur,'unit':basis,'raw':m.group(0),'start':m.start(),'end':m.end()})
    unique=[]; seen=set()
    for x in sorted(out,key=lambda z:z['start']):
        k=(x['start'],x['end'],x['currency'],x['value'])
        if k not in seen: seen.add(k); unique.append(x)
    return unique[:20]


def extract_dates(text: str) -> list[dict]:
    t=clean_text(text); out=[]
    for m in re.finditer(r'\b(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})\b',t):
        try: dt=datetime(int(m.group(1)),int(m.group(2)),int(m.group(3))).date().isoformat()
        except ValueError: continue
        out.append({'value':dt,'raw':m.group(0),'start':m.start(),'end':m.end()})
    return out[:20]


def extract_contacts_normalized(text: str, url: str | None = None) -> dict:
    t=clean_text(text)
    emails=sorted(set(re.findall(r'\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b',t,re.I)))[:20]
    raw_phones=re.findall(r'(?<!\d)(?:\+?\d[\d\s().-]{7,}\d)(?!\d)',t)
    phones=[]
    for p in raw_phones:
        n=re.sub(r'[^0-9+]','',p)
        if len(re.sub(r'\D','',n))>=8 and n not in phones: phones.append(n)
    domain=None
    if url:
        try:
            host=urlparse(url).netloc.lower().split('@')[-1].split(':')[0]
            domain=host[4:] if host.startswith('www.') else host
        except ValueError: pass
    return {'emails':emails,'phones':phones[:20],'domain':domain}


def normalize_commercial_text(text: str, *, source_url: str | None = None, source_title: str | None = None, requested_product: str | None = None) -> dict:
    t=clean_text(text)
    quantities=extract_quantities(t); prices=extract_prices(t); dates=extract_dates(t); contacts=extract_contacts_normalized(t,source_url)
    product=requested_product if requested_product and clean_text(requested_product).lower() in t.lower() else None
    evidence=[]
    for group in (quantities,prices,dates):
        evidence.extend({'type':'quantity' if group is quantities else 'price' if group is prices else 'date','raw':x['raw'],'start':x['start'],'end':x['end']} for x in group)
    return {
        'raw_text':text,
        'source_url':source_url,
        'source_title':source_title,
        'product':product,
        'quantities':quantities,
        'prices':prices,
        'dates':dates,
        'contacts':contacts,
        'evidence_spans':evidence,
        'normalization_version':'24.9.0',
    }
