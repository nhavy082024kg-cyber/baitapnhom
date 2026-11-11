from datetime import datetime
from decimal import Decimal
from typing import Optional

from domain.models.base import entity


@entity
class Order:
    id: Optional[int] = None
    tenant_id: int
    order_code: str
    machine_id: int
    slot_id: int
    product_id: int
    price: Decimal                    # fixed at creation (business rule)
    currency: str = "VND"
    status: str = "CREATED"
    expires_at: datetime
    promotion_id: Optional[int] = None
    paid_at: Optional[datetime] = None
    dispensed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


@entity
class OrderStatusHistory:
    id: Optional[int] = None
    tenant_id: int
    order_id: int
    from_status: Optional[str] = None
    to_status: str
    reason: Optional[str] = None
    actor_type: str = "SYSTEM"
    actor_id: Optional[int] = None
    created_at: Optional[datetime] = None


@entity
class Payment:
    id: Optional[int] = None
    tenant_id: int
    order_id: int
    payment_reference: str
    provider: str
    amount: Decimal
    currency: str = "VND"
    status: str = "WAITING"
    qr_content: Optional[str] = None
    provider_transaction_id: Optional[str] = None
    paid_at: Optional[datetime] = None
    reconciled: bool = False
    created_at: Optional[datetime] = None


@entity
class WebhookEvent:
    id: Optional[int] = None
    tenant_id: Optional[int] = None
    payment_id: Optional[int] = None
    provider_event_id: str
    payload: dict
    signature_valid: bool = True
    processed: bool = False
    received_at: datetime


@entity
class Refund:
    id: Optional[int] = None
    tenant_id: int
    order_id: int
    payment_id: int
    amount: Decimal
    reason: str
    status: str = "REQUESTED"
    requested_by: Optional[int] = None
    approved_by: Optional[int] = None
    provider_refund_id: Optional[str] = None
    created_at: Optional[datetime] = None
