"""Map-ready, evidence-aware geospatial export for commercial intelligence.

Only persisted coordinates are exported. This module deliberately never geocodes
city/address strings or fabricates locations.
"""
from __future__ import annotations

from math import isfinite
from typing import Any


def valid_coordinates(latitude: Any, longitude: Any) -> bool:
    """Accept only finite WGS84 coordinates within legal bounds."""
    if isinstance(latitude, bool) or isinstance(longitude, bool):
        return False
    try:
        lat, lon = float(latitude), float(longitude)
    except (TypeError, ValueError):
        return False
    return isfinite(lat) and isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180


def feature(entity_type: str, entity_id: int, name: str, latitude: Any, longitude: Any,
            country: str | None = None, city: str | None = None,
            verification_status: str | None = None, confidence: Any = None,
            source_url: str | None = None, source_title: str | None = None,
            observed_at: Any = None) -> dict | None:
    if not valid_coordinates(latitude, longitude):
        return None
    lat, lon = float(latitude), float(longitude)
    try:
        confidence_value = float(confidence) if confidence is not None else None
        if confidence_value is not None and (not isfinite(confidence_value) or not 0 <= confidence_value <= 1):
            confidence_value = None
    except (TypeError, ValueError):
        confidence_value = None
    properties = {
        "entity_type": entity_type,
        "entity_id": int(entity_id),
        "name": str(name or f"{entity_type} #{entity_id}"),
        "country": country,
        "city": city,
        "verification_status": verification_status or "Unknown",
        "confidence": confidence_value,
        "source_url": source_url,
        "source_title": source_title,
        "observed_at": observed_at.isoformat() if hasattr(observed_at, "isoformat") else observed_at,
        "location_basis": "stored_coordinates",
    }
    return {"type": "Feature", "id": f"{entity_type}:{entity_id}",
            "geometry": {"type": "Point", "coordinates": [lon, lat]}, "properties": properties}


def in_bbox(feature_item: dict, bbox: tuple[float, float, float, float] | None) -> bool:
    if bbox is None:
        return True
    lon, lat = feature_item["geometry"]["coordinates"]
    west, south, east, north = bbox
    # Handle antimeridian-crossing viewports (west > east).
    longitude_inside = west <= lon <= east if west <= east else lon >= west or lon <= east
    return longitude_inside and south <= lat <= north


def feature_collection(features: list[dict], bbox: tuple[float, float, float, float] | None = None,
                       limit: int = 500) -> dict:
    valid = [item for item in features if item and in_bbox(item, bbox)]
    valid.sort(key=lambda item: (item["properties"].get("entity_type", ""), item["id"]))
    capped = valid[:max(1, min(int(limit), 2000))]
    return {"type": "FeatureCollection", "features": capped,
            "meta": {"returned": len(capped), "matched": len(valid), "truncated": len(valid) > len(capped),
                     "coordinate_policy": "Only valid, explicitly stored WGS84 coordinates; no inferred geocoding."}}
