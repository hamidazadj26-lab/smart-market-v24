from __future__ import annotations
from typing import Any
import asyncio
import json
import httpx

class GoogleMapsError(RuntimeError):
    pass

class GoogleMapsAdapter:
    """Bounded adapter for Google Places/Routes APIs."""
    def __init__(self, api_key: str, timeout: float = 12.0, max_retries: int = 2):
        if not api_key: raise GoogleMapsError("Google Maps API Key تنظیم نشده است.")
        self.api_key = api_key; self.timeout=max(1.0,min(float(timeout),60.0)); self.max_retries=max(0,min(int(max_retries),3))

    async def _post(self, url: str, headers: dict[str,str], payload: dict[str,Any]) -> dict[str,Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(self.max_retries+1):
                try: response=await client.post(url,headers=headers,json=payload)
                except httpx.TimeoutException as exc:
                    if attempt<self.max_retries: await asyncio.sleep(0.25*(2**attempt)); continue
                    raise GoogleMapsError("مهلت پاسخ Google Maps تمام شد.") from exc
                except httpx.HTTPError as exc:
                    if attempt<self.max_retries: await asyncio.sleep(0.25*(2**attempt)); continue
                    raise GoogleMapsError("ارتباط با Google Maps برقرار نشد.") from exc
                if response.status_code==429 or response.status_code>=500:
                    if attempt<self.max_retries:
                        await asyncio.sleep(0.25*(2**attempt)); continue
                    raise GoogleMapsError(f"Google Maps خطای موقت HTTP {response.status_code} داد.")
                if response.status_code>=400:
                    raise GoogleMapsError(f"Google Maps خطای HTTP {response.status_code} داد.")
                try: payload=response.json()
                except (ValueError,json.JSONDecodeError) as exc: raise GoogleMapsError("پاسخ Google Maps قابل پردازش نیست.") from exc
                if not isinstance(payload,dict): raise GoogleMapsError("ساختار پاسخ Google Maps نامعتبر است.")
                return payload
        raise GoogleMapsError("خطای ناشناخته Google Maps")

    async def places_text_search(self, query: str, *, language_code: str = "en", max_result_count: int = 20) -> dict[str, Any]:
        query=(query or "").strip()
        if not query: raise GoogleMapsError("عبارت جستجو نمی‌تواند خالی باشد.")
        return await self._post("https://places.googleapis.com/v1/places:searchText", {"Content-Type":"application/json","X-Goog-Api-Key":self.api_key,"X-Goog-FieldMask":"places.id,places.displayName,places.formattedAddress,places.location,places.nationalPhoneNumber,places.websiteUri,places.types,places.googleMapsUri"}, {"textQuery":query,"languageCode":language_code,"pageSize":max(1,min(int(max_result_count),20))})

    async def compute_route(self, origin: str | dict[str,float], destination: str | dict[str,float], *, language_code: str = "en") -> dict[str, Any]:
        return await self._post("https://routes.googleapis.com/directions/v2:computeRoutes", {"Content-Type":"application/json","X-Goog-Api-Key":self.api_key,"X-Goog-FieldMask":"routes.distanceMeters,routes.duration,routes.polyline.encodedPolyline,routes.legs"}, {"origin":self._waypoint(origin),"destination":self._waypoint(destination),"travelMode":"DRIVE","routingPreference":"TRAFFIC_AWARE","languageCode":language_code,"units":"METRIC"})

    @staticmethod
    def _waypoint(value: str | dict[str,float]) -> dict[str,Any]:
        if isinstance(value,dict):
            try: lat=float(value["latitude"]); lon=float(value["longitude"])
            except (KeyError,TypeError,ValueError) as exc: raise GoogleMapsError("مختصات مبدأ یا مقصد نامعتبر است.") from exc
            if not (-90<=lat<=90 and -180<=lon<=180): raise GoogleMapsError("مختصات مبدأ یا مقصد خارج از محدوده است.")
            return {"location":{"latLng":{"latitude":lat,"longitude":lon}}}
        value=(value or "").strip()
        if not value: raise GoogleMapsError("مبدأ یا مقصد الزامی است.")
        return {"address":value}

def normalize_places(payload: dict[str,Any]) -> list[dict[str,Any]]:
    places=payload.get("places",[]) if isinstance(payload,dict) else []
    if not isinstance(places,list): return []
    results=[]
    for place in places:
        if not isinstance(place,dict): continue
        location=place.get("location") if isinstance(place.get("location"),dict) else {}
        display=place.get("displayName") if isinstance(place.get("displayName"),dict) else {}
        results.append({"place_id":place.get("id"),"name":display.get("text"),"address":place.get("formattedAddress"),"latitude":location.get("latitude"),"longitude":location.get("longitude"),"phone":place.get("nationalPhoneNumber"),"website":place.get("websiteUri"),"types":place.get("types",[]) if isinstance(place.get("types",[]),list) else [],"maps_url":place.get("googleMapsUri")})
    return results

def normalize_route(payload: dict[str,Any]) -> dict[str,Any]:
    routes=payload.get("routes") or [] if isinstance(payload,dict) else []
    if not isinstance(routes,list) or not routes: return {"found":False}
    route=routes[0] if isinstance(routes[0],dict) else {}
    duration=route.get("duration"); seconds=None
    if isinstance(duration,str) and duration.endswith("s"):
        try: seconds=float(duration[:-1])
        except ValueError: pass
    meters=route.get("distanceMeters")
    try: distance_km=float(meters or 0)/1000
    except (TypeError,ValueError): distance_km=0
    return {"found":True,"distance_km":distance_km,"duration_seconds":seconds,"duration_text":duration,"encoded_polyline":(route.get("polyline") or {}).get("encodedPolyline") if isinstance(route.get("polyline"),dict) else None}
