from flask import Blueprint, g, request

from api.middleware import login_required
from api.requests import int_arg, validate_json
from api.responses import ok
from api.schemas.order import RefundSchema
from dependency_container import container

order_bp = Blueprint("orders", __name__, url_prefix="/api/v1/orders")


@order_bp.route("", methods=["GET"])
@login_required
def list_orders():
    """Search orders: ?status=&machine_id=&limit=  or  ?review_queue=true (paid but spray not confirmed)."""
    return ok(container.order_service().list_orders(
        g.ctx, status=request.args.get("status"), machine_id=int_arg("machine_id"),
        review_queue=request.args.get("review_queue", "false").lower() == "true", limit=int_arg("limit", 100)))


@order_bp.route("/<int:order_id>", methods=["GET"])
@login_required
def get_order(order_id):
    """Order with payment, status history, dispense commands and refunds (end-to-end trace)."""
    return ok(container.order_service().get_order_detail(g.ctx, order_id))


@order_bp.route("/<int:order_id>/refund", methods=["POST"])
@login_required
@validate_json(RefundSchema)
def refund_order(order_id):
    """Refund an order that was paid but not dispensed. Needs permission order.refund + step-up."""
    return ok(container.order_service().refund_order(g.ctx, order_id, g.json["reason"]), 201)
