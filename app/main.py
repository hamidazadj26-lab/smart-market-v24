from fastapi import FastAPI, Depends, Request, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import datetime, timezone
import re
import hashlib
from .config import get_settings
from .database import get_db
from .models import *
from .schemas import *
from .security.auth import *
from .services.rbac import ROLES, permissions_for, require_permission, audit, enforce_mutation_permission
from .services.multi_market import get_or_create_market, serialize_market, DEFAULT_WEIGHTS, resolve_market
from .services.trade_rules import serialize_country, serialize_rule, trade_readiness, RULE_TYPES, STATUSES
from .services.product_compliance import compliance_gate, serialize_profile as serialize_compliance, serialize_requirement, STATUSES as COMPLIANCE_STATUSES, REQ_TYPES
from .services.import_cost import find_verified_rule, calculate_import_cost, serialize_rule as serialize_import_rule, STATUSES as IMPORT_COST_STATUSES
from .services.core import *
from .services.commercial import calculate_offer, deal_decision_engine
from .services.negotiation import negotiation_engine
from .services.opportunity_health import calculate_opportunity_health
from .discovery.engine import discover_from_signal, classify_signal
from .adapters.google_maps import GoogleMapsAdapter, GoogleMapsError, normalize_places, normalize_route
from .adapters.divar import DivarAdapter, DivarError, normalize_posts
from .adapters.firecrawl import FirecrawlAdapter, FirecrawlError, normalize_search
from .discovery.engine import parse_demand
from .discovery.sources import BUILTIN_SOURCES, build_queries, resolve_sources
from .discovery.source_discovery import extract_domains, register_discovered
from .verification.intelligence import canonical_key, source_trust, evidence_score, update_candidate_trust, find_candidate_duplicates, merge_candidate
from .routers.system import router as system_router
from .routers.data import router as data_router
from .routers.discovery import router as discovery_router
from .routers.markets import router as markets_router
from .routers.transactions import router as transactions_router
from .routers.intelligence import router as intelligence_router
from .routers.remaining import router as remaining_router
from .services.request_guard import auth, serialize
from .services.freshness import apply_freshness
from pathlib import Path
import logging
import secrets

settings=get_settings(); logging.basicConfig(level=logging.INFO)
app=FastAPI(title=settings.app_name,version=settings.version,debug=settings.debug)
app.add_middleware(CORSMiddleware,allow_origins=settings.cors_list,allow_credentials=True,allow_methods=['GET','POST','PUT','PATCH','DELETE'],allow_headers=['Content-Type'])

@app.middleware("http")
async def security_and_request_id(request, call_next):
    request_id=request.headers.get("X-Request-ID") or secrets.token_hex(12)
    if settings.environment.lower()=="production" and request.method in {"POST","PUT","PATCH","DELETE"}:
        origin=request.headers.get("origin")
        # Cookie-authenticated browser mutations must carry an explicitly trusted
        # Origin. Missing Origin is not treated as permission to bypass the check.
        if request.cookies.get("sm_session") and (not origin or origin not in settings.cors_list):
            return JSONResponse(status_code=403, content={"detail":"Origin not allowed"}, headers={"X-Request-ID":request_id})
        if origin and origin not in settings.cors_list:
            return JSONResponse(status_code=403, content={"detail":"Origin not allowed"}, headers={"X-Request-ID":request_id})
    response=await call_next(request)
    response.headers["X-Request-ID"]=request_id
    response.headers["X-Content-Type-Options"]="nosniff"
    response.headers["X-Frame-Options"]="DENY"
    response.headers["Referrer-Policy"]="same-origin"
    if settings.environment.lower()=="production":
        response.headers["Strict-Transport-Security"]="max-age=31536000; includeSubDomains"
    return response
static=Path(__file__).resolve().parent.parent/'static'
app.mount('/static',StaticFiles(directory=static),name='static')
app.include_router(system_router)
app.include_router(data_router)
app.include_router(discovery_router)
app.include_router(markets_router)
app.include_router(transactions_router)
app.include_router(intelligence_router)
app.include_router(remaining_router)

