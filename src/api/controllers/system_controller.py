from flask import Blueprint, g, request

from api.middleware import login_required
from api.requests import int_arg, validate_json
from api.responses import ok
from api.schemas.order import ResolveAlertSchema
from dependency_container import container
from domain.constants import P

system_bp = Blueprint("system", __name__, url_prefix="/api/v1")


@system_bp.route("/health", methods=["GET"])
def health():
    """Liveness probe."""
    return ok({"service": "scentstation", "status": "up"})


@system_bp.route("/system/jobs/run", methods=["POST"])
@login_required
def run_jobs():
    """Run the background jobs once (Super Admin): expire unpaid orders, time out stuck dispense commands,
    mark silent machines OFFLINE. In production call it every minute from cron / a scheduler."""
    g.ctx.require_permission(P.JOBS_RUN)
    return ok({"expired_orders": container.order_service().expire_overdue(),
               "timed_out_commands": container.dispensing_service().expire_stale_commands(),
               "machines_changed": container.machine_service().refresh_connectivity()})


@system_bp.route("/audit-logs", methods=["GET"])
@login_required
def audit_logs():
    """Search the audit trail: ?action=REFUND&order_id=12&limit=50 (brand users: own brand only)."""
    return ok(container.audit_service().search(g.ctx, action=request.args.get("action"),
                                               order_id=int_arg("order_id"), limit=int_arg("limit", 100)))


@system_bp.route("/alerts", methods=["GET"])
@login_required
def list_alerts():
    """List alerts: ?status=OPEN|ACKNOWLEDGED|RESOLVED."""
    return ok(container.alert_service().list_alerts(g.ctx, request.args.get("status"), int_arg("limit", 100)))


@system_bp.route("/alerts/<int:alert_id>/acknowledge", methods=["POST"])
@login_required
def acknowledge_alert(alert_id):
    """Acknowledge an alert."""
    return ok(container.alert_service().acknowledge(g.ctx, alert_id))


@system_bp.route("/alerts/<int:alert_id>/resolve", methods=["POST"])
@login_required
@validate_json(ResolveAlertSchema)
def resolve_alert(alert_id):
    """Resolve an alert with a note."""
    return ok(container.alert_service().resolve(g.ctx, alert_id, g.json.get("note")))
