from app.services.rbac import ROLES, permissions_for

def test_roles_exist():
 assert {'Super Admin','Admin','Sales','Procurement','Logistics','Analyst','Viewer'} <= set(ROLES)

def test_super_admin_is_full_access(): assert permissions_for('Super Admin')==['*']

def test_viewer_has_no_user_management(): assert 'user.manage' not in ROLES['Viewer']
