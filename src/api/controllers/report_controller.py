from flask import Blueprint, Response, g, request

from api.middleware import login_required
from api.requests import validate_json
from api.responses import ok
from api.schemas.ops import ReconcileSchema
from dependency_container import container

report_bp = Blueprint("reports", __name__, url_prefix="/api/v1/reports")


def _csv_response(text: str, filename: str) -> Response:
    return Response(text, mimetype="text/csv", headers={"Content-Disposition": f"attachment; filename={filename}"})


@report_bp.route("/dashboard", methods=["GET"])
@login_required
def dashboard():
    """Brand dashboard: ?from=2026-11-01&to=2026-11-30 (default: last 30 days). Machines, orders, revenue,
    dispensing success rate, top fragrances, low-stock slots, alerts and maintenance."""
    return ok(container.report_service().dashboard(g.ctx, request.args.get("from"), request.args.get("to")))


@report_bp.route("/platform", methods=["GET"])
@login_required
def platform_overview():
    """Platform-wide statistics (Super Admin only): ?from=&to="""
    return ok(container.report_service().platform_overview(g.ctx, request.args.get("from"), request.args.get("to")))


@report_bp.route("/transactions.csv", methods=["GET"])
@login_required
def transactions_csv():
    """Download transactions as CSV: ?from=&to="""
    text = container.report_service().export_transactions_csv(g.ctx, request.args.get("from"), request.args.get("to"))
    return _csv_response(text, "transactions.csv")


@report_bp.route("/inventory.csv", methods=["GET"])
@login_required
def inventory_csv():
    """Download the bottle inventory as CSV."""
    return _csv_response(container.report_service().export_inventory_csv(g.ctx), "inventory.csv")


@report_bp.route("/reconciliation", methods=["POST"])
@login_required
@validate_json(ReconcileSchema)
def reconcile():
    """Reconcile our payments with the payment provider's statement. Matching payments are marked reconciled."""
    return ok(container.report_service().reconcile(g.ctx, g.json["records"], g.json["start"], g.json["end"]))
