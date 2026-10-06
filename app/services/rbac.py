from fastapi import HTTPException, Request
from sqlalchemy.orm import Session
from ..models import Admin, AuditLog

ROLES={
    'Super Admin': {'*'},
    'Admin': {'dashboard.read','command_center.read','opportunity.read','opportunity.write','customer.write','manufacturer.write','demand.write','rfq.write','commercial.write','logistics.write','verification.write','data_quality.read','watchtower.read','watchtower.write','automation.run','audit.read','user.manage','market_rules.read','market_rules.write'},
    'Sales': {'dashboard.read','command_center.read','opportunity.read','opportunity.write','customer.write','manufacturer.read','demand.read','rfq.write','commercial.read','logistics.read','verification.read','data_quality.read','watchtower.read','watchtower.write','automation.run','market_rules.read'},
    'Procurement': {'dashboard.read','command_center.read','opportunity.read','opportunity.write','customer.read','manufacturer.write','demand.write','rfq.write','commercial.write','logistics.read','verification.write','data_quality.read','watchtower.read','watchtower.write','automation.run','market_rules.read'},
    'Logistics': {'dashboard.read','command_center.read','opportunity.read','customer.read','manufacturer.read','demand.read','commercial.read','logistics.write','verification.read','data_quality.read','watchtower.read','market_rules.read'},
    'Analyst': {'dashboard.read','command_center.read','opportunity.read','customer.read','manufacturer.read','demand.read','commercial.read','logistics.read','verification.read','data_quality.read','watchtower.read','watchtower.write','audit.read','market_rules.read'},
    'Viewer': {'dashboard.read','command_center.read','opportunity.read','customer.read','manufacturer.read','demand.read','commercial.read','logistics.read','verification.read','data_quality.read','watchtower.read','market_rules.read'},
}

def permissions_for(role):
    return sorted(ROLES.get(role,set()))

def mutation_permission(request):
    """Return the least-privilege permission required for a mutating API call."""
    path=request.url.path
    if path in {'/api/search','/api/discovery/classify','/api/places/search','/api/routes'}:
        return None
    if path.startswith('/api/admins'):
        return 'user.manage'
    if path.startswith('/api/watchtower'):
        return 'watchtower.write'
    if path.startswith('/api/automation'):
        return 'automation.run'
    if path.startswith('/api/verify') or path.startswith('/api/verification'):
        return 'verification.write'
    if path.startswith('/api/trade-rules') or path.startswith('/api/country-profiles') or path.startswith('/api/import-cost-rules') or path.startswith('/api/product-compliance') or path.startswith('/api/compliance-requirements'):
        return 'market_rules.write'
    if '/rfq' in path or '/communications' in path:
        return 'rfq.write'
    if '/logistics' in path or '/trade-routes' in path:
        return 'logistics.write'
    if '/supplier-quotes' in path or '/commercial-offers' in path or '/commercial-comparison' in path or '/deal-decision' in path or '/negotiation-intelligence' in path or '/trade-optimizer' in path or path.startswith('/api/market-prices'):
        return 'commercial.write'
    if path.startswith('/api/markets'):
        return 'market_rules.write'
    if path.startswith('/api/sources') or path.startswith('/api/products') or path.startswith('/api/manufacturers') or path.startswith('/api/customers') or path.startswith('/api/demands') or path.startswith('/api/signals') or path.startswith('/api/discovery') or path.startswith('/api/opportunities'):
        return 'opportunity.write'
    return 'opportunity.write'

def enforce_mutation_permission(request, admin):
    if request.method.upper() not in {'POST','PUT','PATCH','DELETE'}:
        return admin
    permission=mutation_permission(request)
    if permission is None or '*' in ROLES.get(admin.role or 'Viewer',set()):
        return admin
    if permission not in ROLES.get(admin.role or 'Viewer',set()):
        raise HTTPException(403,'دسترسی کافی برای این عملیات وجود ندارد.')
    return admin

def require_permission(request:Request,db:Session,permission:str):
    from ..security.auth import get_admin
    a=get_admin(request,db)
    grants=ROLES.get(a.role or 'Viewer',set())
    if '*' not in grants and permission not in grants:
        raise HTTPException(403,'دسترسی کافی برای این عملیات وجود ندارد.')
    return a

def audit(db,admin,action,entity_type=None,entity_id=None,details=None):
    db.add(AuditLog(admin_id=admin.id,action=action,entity_type=entity_type,entity_id=entity_id,details=details or {}))
