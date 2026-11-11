from flask import Blueprint, g

from api.middleware import login_required
from api.requests import validate_json
from api.responses import ok
from api.schemas.tenant import CreateTenantSchema, CreateUserSchema, TenantStatusSchema, UserStatusSchema
from dependency_container import container

tenant_bp = Blueprint("tenants", __name__, url_prefix="/api/v1/tenants")
user_bp = Blueprint("users", __name__, url_prefix="/api/v1/users")


# ------------------------------------------------------------------ brands (Super Admin)
@tenant_bp.route("", methods=["POST"])
@login_required
@validate_json(CreateTenantSchema)
def create_tenant():
    """Create a perfume brand (tenant). Super Admin only."""
    return ok(container.tenant_service().create_tenant(g.ctx, **g.json), 201)


@tenant_bp.route("", methods=["GET"])
@login_required
def list_tenants():
    """List all brands. Super Admin only."""
    return ok(container.tenant_service().list_tenants(g.ctx))


@tenant_bp.route("/<int:tenant_id>", methods=["GET"])
@login_required
def get_tenant(tenant_id):
    """Get one brand."""
    return ok(container.tenant_service().get_tenant(g.ctx, tenant_id))


@tenant_bp.route("/<int:tenant_id>/status", methods=["PATCH"])
@login_required
@validate_json(TenantStatusSchema)
def set_tenant_status(tenant_id):
    """Activate / suspend a brand. Suspending ends every session of that brand immediately."""
    return ok(container.tenant_service().set_status(g.ctx, tenant_id, g.json["status"]))


# ------------------------------------------------------------------ users
@user_bp.route("", methods=["POST"])
@login_required
@validate_json(CreateUserSchema)
def create_user():
    """Create a user with roles.

    Brand Admin: creates users inside their own brand. Super Admin: must send tenant_id (creates a Brand Admin).
    """
    return ok(container.user_service().create_user(g.ctx, **g.json), 201)


@user_bp.route("", methods=["GET"])
@login_required
def list_users():
    """List users of my brand (Super Admin: all users)."""
    return ok(container.user_service().list_users(g.ctx))


@user_bp.route("/<int:user_id>/status", methods=["PATCH"])
@login_required
@validate_json(UserStatusSchema)
def set_user_status(user_id):
    """Activate / deactivate / lock a user. Deactivating revokes all of the user's sessions."""
    return ok(container.user_service().set_status(g.ctx, user_id, g.json["status"]))
