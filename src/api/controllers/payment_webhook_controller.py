import json
import uuid

from flask import Blueprint, current_app, g, request

from api.middleware import login_required
from api.requests import validate_json
from api.responses import ok
from api.schemas.order import MockPaymentSchema
from dependency_container import container
from domain.exceptions import NotFoundException

webhook_bp = Blueprint("webhooks", __name__, url_prefix="/api/v1")


@webhook_bp.route("/webhooks/payment", methods=["POST"])
def payment_webhook():
    """Payment provider callback (no login: authenticated by the X-Signature HMAC of the RAW body).

    Duplicate events are ignored (idempotent). Only here can a payment become SUCCESS.
    """
    return ok(container.payment_service().handle_webhook(request.get_data(), request.headers.get("X-Signature")))


@webhook_bp.route("/dev/mock-payment", methods=["POST"])
@validate_json(MockPaymentSchema)
def mock_payment():
    """DEV ONLY (MOCK_PAYMENT_ENABLED=true): pretend to be the payment provider and send a signed webhook.

    Send the same event_id twice to see idempotency; change amount to see the mismatch protection.
    """
    if not current_app.config.get("MOCK_PAYMENT_ENABLED"):
        raise NotFoundException("Not found")
    data = g.json
    payment = container.payment_repository().get_by_reference(data["payment_reference"])
    amount = data.get("amount") if data.get("amount") is not None else (payment.amount if payment else 0)
    body = json.dumps({"event_id": data.get("event_id") or uuid.uuid4().hex,
                       "payment_reference": data["payment_reference"], "amount": str(amount),
                       "currency": data["currency"], "status": data["status"]}).encode()
    provider = container.payment_provider()
    return ok(container.payment_service().handle_webhook(body, provider.sign(body)))
