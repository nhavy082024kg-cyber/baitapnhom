from sqlalchemy import JSON, Boolean, CHAR, Column, DateTime, Numeric, String, Text

from domain.constants import ActorType, OrderStatus, PaymentStatus, RefundStatus
from infrastructure.databases.base import Base
from infrastructure.models.mixins import IdMixin, TimestampMixin, enum_col, fk, id_type


class OrderModel(IdMixin, TimestampMixin, Base):
    """ERD 1.16 orders (product + price are frozen at creation)."""
    __tablename__ = "orders"

    tenant_id = fk("tenants.id", nullable=False)
    order_code = Column(String(40), nullable=False, unique=True)
    machine_id = fk("machines.id", nullable=False)
    slot_id = fk("slots.id", nullable=False)
    product_id = fk("products.id", nullable=False)
    promotion_id = fk("promotions.id")
    price = Column(Numeric(12, 2), nullable=False)
    currency = Column(CHAR(3), nullable=False, default="VND")
    status = enum_col(OrderStatus, default=OrderStatus.CREATED)
    expires_at = Column(DateTime, nullable=False, index=True)
    paid_at = Column(DateTime)
    dispensed_at = Column(DateTime)


class OrderStatusHistoryModel(IdMixin, TimestampMixin, Base):
    """ERD 1.17 order_status_history."""
    __tablename__ = "order_status_history"

    tenant_id = fk("tenants.id", nullable=False)
    order_id = fk("orders.id", nullable=False)
    from_status = Column(String(30))
    to_status = Column(String(30), nullable=False)
    reason = Column(String(255))
    actor_type = enum_col(ActorType, default=ActorType.SYSTEM)
    actor_id = Column(id_type())                    # user id, machine id... depending on actor_type (no FK)


class PaymentModel(IdMixin, TimestampMixin, Base):
    """ERD 1.18 payments (exactly one per order)."""
    __tablename__ = "payments"

    tenant_id = fk("tenants.id", nullable=False)
    order_id = fk("orders.id", nullable=False, unique=True)
    payment_reference = Column(String(64), nullable=False, unique=True)
    provider = Column(String(50), nullable=False)
    provider_transaction_id = Column(String(100), unique=True)
    qr_content = Column(Text)
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(CHAR(3), nullable=False, default="VND")
    status = enum_col(PaymentStatus, default=PaymentStatus.WAITING)
    paid_at = Column(DateTime)
    reconciled = Column(Boolean, nullable=False, default=False)
    reconciled_at = Column(DateTime)


class PaymentWebhookEventModel(IdMixin, TimestampMixin, Base):
    """ERD 1.19 payment_webhook_events: UNIQUE provider_event_id = idempotency."""
    __tablename__ = "payment_webhook_events"

    tenant_id = fk("tenants.id")
    payment_id = fk("payments.id")
    provider_event_id = Column(String(100), nullable=False, unique=True)
    payload = Column(JSON, nullable=False)
    signature_valid = Column(Boolean, nullable=False, default=True)
    processed = Column(Boolean, nullable=False, default=False)
    received_at = Column(DateTime, nullable=False)


class RefundModel(IdMixin, TimestampMixin, Base):
    """ERD 1.20 refunds."""
    __tablename__ = "refunds"

    tenant_id = fk("tenants.id", nullable=False)
    order_id = fk("orders.id", nullable=False)
    payment_id = fk("payments.id", nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    reason = Column(String(255), nullable=False)
    status = enum_col(RefundStatus, default=RefundStatus.REQUESTED)
    requested_by = fk("users.id")
    approved_by = fk("users.id")
    provider_refund_id = Column(String(100))
