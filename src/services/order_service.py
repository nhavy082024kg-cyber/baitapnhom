import uuid
from datetime import timedelta
from typing import List, Optional

from domain.clock import utcnow
from domain.constants import ActorType, OrderStatus, P, PaymentStatus, REVIEW_QUEUE_STATUSES, RefundStatus
from domain.exceptions import BusinessRuleException, ConflictException, NotFoundException
from domain.models.dispense_policy import assert_can_accept_order, machine_block_reason, slot_block_reason
from domain.models.irepositories import (IDispenseCommandRepository, IMachineRepository, IOrderRepository,
                                         IPaymentRepository, IProductRepository, IRefundRepository,
                                         ISlotRepository, IUnitOfWork)
from domain.models.iservices import IPaymentProvider
from domain.models.machine import Machine
from domain.models.order import Order, Payment, Refund
from domain.models.settings import ServiceSettings
from domain.models.user import AuthContext
from services.audit_service import AuditService
from services.common import new_code
from services.order_workflow import OrderWorkflow

KIOSK_MESSAGES = {
    "AWAITING_PAYMENT": "Scan the QR code to pay.",
    "PAID": "Payment received. Preparing your spray...",
    "DISPENSING": "Place your test strip or wrist in the spray area.",
    "DISPENSED": "Done! Enjoy your fragrance.",
    "DISPENSE_FAILED": "Payment received but the spray failed. Please keep your order code for a refund.",
    "UNCERTAIN": "We could not confirm your spray. Please keep your order code, we will review it.",
    "MANUAL_REVIEW": "Payment received but the spray was not completed. Keep your order code: we will refund you.",
    "EXPIRED": "The payment time has expired. Please start again.",
    "CANCELLED": "The order was cancelled.",
    "REFUNDED": "Your payment has been refunded.",
}


class OrderService:
    def __init__(self, orders: IOrderRepository, payments: IPaymentRepository, slots: ISlotRepository,
                 products: IProductRepository, machines: IMachineRepository, refunds: IRefundRepository,
                 commands: IDispenseCommandRepository, provider: IPaymentProvider, workflow: OrderWorkflow,
                 audit: AuditService, uow: IUnitOfWork, settings: ServiceSettings, clock=utcnow):
        self.orders = orders
        self.payments = payments
        self.slots = slots
        self.products = products
        self.machines = machines
        self.refunds = refunds
        self.commands = commands
        self.provider = provider
        self.workflow = workflow
        self.audit = audit
        self.uow = uow
        self.settings = settings
        self.clock = clock

    # ------------------------------------------------------------------ kiosk (authenticated as the machine)
    def list_catalog(self, machine: Machine) -> dict:
        """Fragrances shown on the kiosk home screen."""
        now = self.clock()
        reason = machine_block_reason(machine, now, self.settings)
        items = []
        for slot in self.slots.list_by_machine(machine.id):
            product = self.products.get(machine.tenant_id, slot.product_id) if slot.product_id else None
            if product is None or not product.is_available or slot_block_reason(slot):
                continue
            items.append({"slot": slot, "product": product})
        return {"orderable": reason is None, "reason": reason, "items": items}

    def create_order(self, machine: Machine, slot_number: int) -> dict:
        now = self.clock()
        slot = self.slots.get_by_number(machine.id, slot_number)
        product = self.products.get(machine.tenant_id, slot.product_id) if slot and slot.product_id else None
        assert_can_accept_order(machine, slot, product, self.machines.has_critical_open_ticket(machine.id),
                                now, self.settings)

        order = self.orders.add(Order(
            tenant_id=machine.tenant_id, order_code=new_code("ORD", 10), machine_id=machine.id, slot_id=slot.id,
            product_id=product.id, price=slot.price, currency="VND", status=OrderStatus.CREATED.value,
            expires_at=now + timedelta(minutes=self.settings.order_ttl_minutes), created_at=now))
        self.workflow.start(order, ActorType.DEVICE.value, machine.id)
        reference = new_code("SS", 16)
        payment = self.payments.add(Payment(
            tenant_id=machine.tenant_id, order_id=order.id, payment_reference=reference,
            provider=self.provider.name, amount=order.price, currency=order.currency,
            status=PaymentStatus.WAITING.value, qr_content=self.provider.build_qr(reference, order.price, order.currency),
            created_at=now))
        self.workflow.transition(order, OrderStatus.AWAITING_PAYMENT.value, ActorType.SYSTEM.value)
        self.uow.commit()
        return {"order": order, "payment": payment, "message": KIOSK_MESSAGES[order.status]}

    def kiosk_order_status(self, machine: Machine, order_code: str) -> dict:
        order = self.orders.get_by_code(order_code)
        if order is None or order.machine_id != machine.id:       # a kiosk only sees its own orders
            raise NotFoundException("Order not found")
        self._expire_if_overdue(order)
        self.uow.commit()
        command = self.commands.get_sale_for_order(order.id)
        return {"order": order, "payment": self.payments.get_by_order(order.id),
                "dispense_status": command.status if command else None,
                "message": KIOSK_MESSAGES.get(order.status, "")}

    # ------------------------------------------------------------------ portal (Operations Manager ...)
    def list_orders(self, ctx: AuthContext, status: Optional[str] = None, machine_id: Optional[int] = None,
                    review_queue: bool = False, limit: int = 100) -> List[Order]:
        ctx.require_permission(P.ORDER_VIEW)
        tenant_id = ctx.require_tenant()
        if review_queue:                       # payment succeeded but spray not confirmed
            result: List[Order] = []
            for s in REVIEW_QUEUE_STATUSES:
                result.extend(self.orders.list(tenant_id, s, machine_id, limit))
            return result[:limit]
        return self.orders.list(tenant_id, status, machine_id, min(limit, 500))

    def get_order_detail(self, ctx: AuthContext, order_id: int) -> dict:
        ctx.require_permission(P.ORDER_VIEW)
        order = self.orders.get(ctx.require_tenant(), order_id)
        if order is None:
            raise NotFoundException("Order not found")
        return {"order": order, "payment": self.payments.get_by_order(order.id),
                "history": self.orders.list_history(order.id), "commands": self.commands.list_for_order(order.id),
                "refunds": self.refunds.list_by_order(order.id)}

    def refund_order(self, ctx: AuthContext, order_id: int, reason: str) -> Refund:
        """Sensitive action: permission + step-up (password re-entered recently)."""
        ctx.require_permission(P.ORDER_REFUND)
        ctx.require_step_up(self.clock())
        order = self.orders.get(ctx.require_tenant(), order_id)
        if order is None:
            raise NotFoundException("Order not found")
        if order.status == OrderStatus.REFUNDED.value:
            raise ConflictException("Order is already refunded")
        if order.status not in REVIEW_QUEUE_STATUSES:
            raise BusinessRuleException(f"Only orders awaiting review can be refunded (status: {order.status})",
                                        "REFUND_NOT_ALLOWED")
        payment = self.payments.get_by_order(order.id)
        if payment is None or payment.status != PaymentStatus.SUCCESS.value:
            raise BusinessRuleException("There is no successful payment to refund", "REFUND_NOT_ALLOWED")
        refund = self.refunds.add(Refund(
            tenant_id=order.tenant_id, order_id=order.id, payment_id=payment.id, amount=payment.amount,
            reason=reason, status=RefundStatus.COMPLETED.value, requested_by=ctx.user_id, approved_by=ctx.user_id,
            provider_refund_id=f"MOCK-RF-{uuid.uuid4().hex[:10].upper()}", created_at=self.clock()))
        self.workflow.transition(order, OrderStatus.REFUNDED.value, ActorType.USER.value, ctx.user_id, reason)
        self.audit.record_user(ctx, "REFUND", "order", target_id=order.id, order_id=order.id,
                               after={"amount": payment.amount, "reason": reason}, severity="WARNING")
        self.uow.commit()
        return refund

    # ------------------------------------------------------------------ background job
    def expire_overdue(self) -> int:
        count = 0
        for order in self.orders.list_overdue_awaiting_payment(self.clock()):
            self._expire_if_overdue(order)
            count += 1
        self.uow.commit()
        return count

    def _expire_if_overdue(self, order: Order) -> None:
        if order.status == OrderStatus.AWAITING_PAYMENT.value and order.expires_at <= self.clock():
            self.workflow.transition(order, OrderStatus.EXPIRED.value, ActorType.SYSTEM.value, reason="Payment timeout")
            payment = self.payments.get_by_order(order.id)
            if payment and payment.status == PaymentStatus.WAITING.value:
                payment.status = PaymentStatus.EXPIRED.value
                self.payments.update(payment)
