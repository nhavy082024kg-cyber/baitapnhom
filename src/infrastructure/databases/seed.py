from domain.constants import ALL_PERMISSIONS, DEFAULT_ROLE_PERMISSIONS, RoleCode, STEP_UP_PERMISSIONS
from infrastructure.models.tenant_model import TenantModel  # noqa: F401
from infrastructure.models.user_models import (PermissionModel, RoleModel, RolePermissionModel, UserModel,
                                               UserRoleModel)
from infrastructure.services.security_service import PasswordHasher


def seed_defaults(session, config) -> None:
    """Idempotent: creates permissions, the 6 system roles and (optionally) the first Super Admin."""
    permissions = {p.code: p for p in session.query(PermissionModel).all()}
    for code in ALL_PERMISSIONS:
        if code not in permissions:
            permissions[code] = PermissionModel(code=code, description=code, requires_step_up=code in STEP_UP_PERMISSIONS)
            session.add(permissions[code])
    session.flush()

    roles = {r.code: r for r in session.query(RoleModel).filter(RoleModel.tenant_id.is_(None)).all()}
    for role_code, perm_codes in DEFAULT_ROLE_PERMISSIONS.items():
        if role_code not in roles:
            roles[role_code] = RoleModel(tenant_id=None, code=role_code, name=role_code.replace("_", " ").title(),
                                         is_system=True)
            session.add(roles[role_code])
            session.flush()
        linked = {rp.permission_id for rp in session.query(RolePermissionModel).filter_by(role_id=roles[role_code].id)}
        for perm_code in perm_codes:
            if permissions[perm_code].id not in linked:
                session.add(RolePermissionModel(role_id=roles[role_code].id, permission_id=permissions[perm_code].id))

    email = (config.get("SEED_SUPER_ADMIN_EMAIL") or "").strip().lower()
    password = config.get("SEED_SUPER_ADMIN_PASSWORD") or ""
    if email and password and session.query(UserModel).filter_by(email=email).first() is None:
        admin = UserModel(tenant_id=None, email=email, full_name="Platform Super Admin",
                          password_hash=PasswordHasher().hash(password), status="ACTIVE")
        session.add(admin)
        session.flush()
        session.add(UserRoleModel(user_id=admin.id, role_id=roles[RoleCode.SUPER_ADMIN.value].id))
    session.commit()
