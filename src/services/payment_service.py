import json
from typing import Optional

from domain.clock import utcnow
from domain.constants import ActorType, OrderStatus, PaymentStatus
from domain.exceptions import BusinessRuleException, NotFoundException, UnauthorizedException, ValidationException
from domain.models.irepositories import IOrderRepository, IPaymentRepository, IUnitOfWork, IWebhookEventRepository
from domain.models.iservices import IPaymentProvider
from domain.models.order import WebhookEvent
from services.audit_service import AuditService
from services.common import to_decimal
from services.dispensing_service import DispensingService
from services.order_workflow import OrderWorkflow

REQUIRED_FIELDS = ("event_id", "payment_reference", "amount", "currency", "status")


class PaymentService:
    """Only the BACKEND can confirm a payment (business rule): a kiosk screen is never proof of payment."""

    def __init__(self, payments: IPaymentRepository, orders: IOrderRepository, webhooks: IWebhookEventRepository,
                 provider: IPaymentProvider, workflow: OrderWorkflow, dispensing: DispensingService,
                 audit: AuditService, uow: IUnitOfWork, clock=utcnow):
        self.payments = payments
        self.orders = orders
        self.webhooks = webhooks
        self.provider = provider
        self.workflow = workflow
        self.dispensing = dispensing
        self.audit = audit
        self.uow = uow
        self.clock = clock

    def handle_webhook(self, raw_body: bytes, signature: Optional[str]) -> dict:
        # 1. signature over the RAW body
        if not self.provider.verify_signature(raw_body, signature):
            self.audit.record(action="WEBHOOK_BAD_SIGNATURE", target_type="payment",
                              actor_type=ActorType.PAYMENT_PROVIDER.value, severity="CRITICAL")
            self.uow.commit()
            raise UnauthorizedException("Invalid webhook signature")

        # 2. payload
        try:
            data = json.loads(raw_body)
        except ValueError:
            raise ValidationException("Body must be JSON")
        missing = [f for f in REQUIRED_FIELDS if f not in data]
        if missing:
            raise ValidationException(f"Missing fields: {missing}")
        status = str(data["status"]).upper()
        now = self.clock()

        payment = self.payments.get_by_reference(data["payment_reference"])
        event = WebhookEvent(tenant_id=payment.tenant_id if payment else None,
                             payment_id=payment.id if payment else None, provider_event_id=str(data["event_id"]),
                             payload=data, signature_valid=True, received_at=now)

        # 3. idempotency: the same provider event is processed only once
        if not self.webhooks.add_if_new(event):
            return {"result": "duplicate_ignored", "event_id": event.provider_event_id}
        if payment is None:
            self.webhooks.mark_processed(event.provider_event_id)
            self.uow.commit()
            raise NotFoundException("Unknown payment reference")

        order = self.orders.get_by_id(payment.order_id)

        # 4. amount / currency must match what we asked the customer to pay
        if to_decimal(data["amount"], "amount") != payment.amount or data["currency"] != payment.currency:
            self.webhooks.mark_processed(event.provider_event_id, payment.id)
            self.audit.record(action="WEBHOOK_AMOUNT_MISMATCH", target_type="payment", target_id=payment.id,
                              order_id=order.id, tenant_id=payment.tenant_id,
                              actor_type=ActorType.PAYMENT_PROVIDER.value,
                              after={"expected": payment.amount, "received": data["amount"]}, severity="CRITICAL")
            self.uow.commit()
            raise BusinessRuleException("Paid amount or currency does not match the order", "AMOUNT_MISMATCH")

        # 5. state changes (single transaction)
        outcome = "ignored"
        if payment.status == PaymentStatus.SUCCESS.value:
            outcome = "already_paid"
        elif status == "SUCCESS":
            payment.status = PaymentStatus.SUCCESS.value
            payment.paid_at = now
            payment.provider_transaction_id = data.get("transaction_id")
            self.payments.update(payment)
            if order.status == OrderStatus.AWAITING_PAYMENT.value:
                self.workflow.transition(order, OrderStatus.PAID.value, ActorType.PAYMENT_PROVIDER.value)
                self.dispensing.create_sale_command(order)      # only here: after verified payment
                outcome = "paid"
            elif order.status in (OrderStatus.EXPIRED.value, OrderStatus.CANCELLED.value):
                # money received for an order we already closed: NEVER spray, humans refund
                self.workflow.transition(order, OrderStatus.MANUAL_REVIEW.value, ActorType.PAYMENT_PROVIDER.value,
                                         reason="Payment received after the order was closed")
                outcome = "paid_after_close"
        elif status in ("FAILED", "CANCELLED"):
            payment.status = status
            self.payments.update(payment)
            if order.status == OrderStatus.AWAITING_PAYMENT.value:
                self.workflow.transition(order, OrderStatus.CANCELLED.value, ActorType.PAYMENT_PROVIDER.value,
                                         reason=f"Payment {status}")
            outcome = status.lower()
        else:
            raise ValidationException("status must be SUCCESS, FAILED or CANCELLED")

        self.webhooks.mark_processed(event.provider_event_id, payment.id)
        self.audit.record(action="PAYMENT_WEBHOOK", target_type="payment", target_id=payment.id, order_id=order.id,
                          tenant_id=payment.tenant_id, actor_type=ActorType.PAYMENT_PROVIDER.value,
                          after={"event_id": event.provider_event_id, "status": status, "outcome": outcome})
        self.uow.commit()
        return {"result": outcome, "event_id": event.provider_event_id, "order_code": order.order_code,
                "order_status": order.status}
