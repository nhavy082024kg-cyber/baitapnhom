from flask import Blueprint, g

from api.middleware import device_required
from api.requests import validate_json
from api.responses import ok
from api.schemas.order import CreateKioskOrderSchema
from dependency_container import container

kiosk_bp = Blueprint("kiosk", __name__, url_prefix="/api/v1/kiosk")


@kiosk_bp.route("/catalog", methods=["GET"])
@device_required
def catalog():
    """Fragrances available on this machine (home screen). `orderable=false` -> show the reason."""
    return ok(container.order_service().list_catalog(g.device))


@kiosk_bp.route("/orders", methods=["POST"])
@device_required
@validate_json(CreateKioskOrderSchema)
def create_order():
    """Customer confirmed a fragrance: create the order and the payment QR (price fixed now)."""
    return ok(container.order_service().create_order(g.device, g.json["slot_number"]), 201)


@kiosk_bp.route("/orders/<order_code>", methods=["GET"])
@device_required
def order_status(order_code):
    """Poll the order: payment status, dispensing status and the message to display."""
    return ok(container.order_service().kiosk_order_status(g.device, order_code))
