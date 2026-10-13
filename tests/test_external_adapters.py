import pytest
import httpx
from app.adapters.firecrawl import FirecrawlAdapter, FirecrawlError, normalize_search
from app.adapters.google_maps import GoogleMapsAdapter, GoogleMapsError, normalize_places

@pytest.mark.asyncio
async def test_firecrawl_retries_transient_http(monkeypatch):
    calls=[]
    class Resp:
        def __init__(self, code, payload=None): self.status_code=code; self.headers={}; self._payload=payload
        def json(self): return self._payload
    async def post(self,*a,**k):
        calls.append(1); return Resp(500 if len(calls)==1 else 200,{"data":[]})
    class Client:
        async def __aenter__(self): return self
        async def __aexit__(self,*a): pass
    Client.post=post
    monkeypatch.setattr(httpx,"AsyncClient",lambda **k: Client())
    result=await FirecrawlAdapter("x",max_retries=1).search("test")
    assert result=={"data":[]}; assert len(calls)==2

@pytest.mark.asyncio
async def test_google_rejects_invalid_json(monkeypatch):
    class Resp:
        status_code=200
        def json(self): raise ValueError("bad")
    async def post(*a,**k): return Resp()
    class Client:
        async def __aenter__(self): return self
        async def __aexit__(self,*a): pass
    Client.post=post
    monkeypatch.setattr(httpx,"AsyncClient",lambda **k: Client())
    with pytest.raises(GoogleMapsError): await GoogleMapsAdapter("x",max_retries=0).places_text_search("test")

def test_normalizers_ignore_malformed_items():
    assert normalize_search({"data":[None,"bad",{"url":"https://x","metadata":{}}]})[0]["url"]=="https://x"
    assert normalize_places({"places":[None,{"id":"p1","displayName":{"text":"X"}}]})[0]["place_id"]=="p1"

from app.adapters.divar import DivarAdapter, DivarError, normalize_posts

@pytest.mark.asyncio
async def test_divar_retries_transient_http(monkeypatch):
    calls=[]
    class Resp:
        def __init__(self, code, payload=None): self.status_code=code; self.headers={}; self._payload=payload
        def json(self): return self._payload
    async def post(*a,**k):
        calls.append(1); return Resp(500 if len(calls)==1 else 200,{"posts":[]})
    class Client:
        async def __aenter__(self): return self
        async def __aexit__(self,*a): pass
    Client.post=post
    monkeypatch.setattr(httpx,"AsyncClient",lambda **k: Client())
    result=await DivarAdapter("x",max_retries=1).search("PET preform")
    assert result=={"posts":[]}; assert len(calls)==2

def test_divar_normalizer_ignores_malformed_posts():
    rows=normalize_posts({"posts":[None,"bad",{}, {"token":"abc","title":"PET preform"}]})
    assert rows[0]["id"]=="abc" and rows[0]["url"].endswith("/abc")
