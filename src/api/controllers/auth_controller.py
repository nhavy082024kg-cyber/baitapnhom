from flask import Blueprint, g, request

from api.middleware import login_required
from api.requests import validate_json
from api.responses import ok
from api.schemas.auth import LoginSchema, StepUpSchema
from dependency_container import container

auth_bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")


@auth_bp.route("/login", methods=["POST"])
@validate_json(LoginSchema)
def login():
    """Log in with email + password and receive a JWT.

    Use it as `Authorization: Bearer <token>`. 5 wrong passwords lock the account.
    """
    result = container.auth_service().login(g.json["email"], g.json["password"], ip=request.remote_addr,
                                            device_info=request.headers.get("User-Agent"))
    return ok({"access_token": result["token"], "token_type": "Bearer", "expires_at": result["expires_at"],
               "user": result["user"], "roles": result["roles"], "permissions": result["permissions"]})


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    """Log out: revokes the current session (the token stops working immediately)."""
    container.auth_service().logout(g.ctx)
    return ok({"logged_out": True})


@auth_bp.route("/me", methods=["GET"])
@login_required
def me():
    """Who am I: user, brand (tenant_id), roles and permissions of the current token."""
    ctx = g.ctx
    return ok({"user_id": ctx.user_id, "tenant_id": ctx.tenant_id, "email": ctx.email, "roles": ctx.roles,
               "permissions": sorted(ctx.permissions), "step_up_verified_until": ctx.step_up_verified_until})


@auth_bp.route("/step-up", methods=["POST"])
@login_required
@validate_json(StepUpSchema)
def step_up():
    """Re-enter the password to unlock sensitive actions (refund, test spray) for a few minutes."""
    return ok(container.auth_service().step_up(g.ctx, g.json["password"]))
