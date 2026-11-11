from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from domain.models.base import entity


@entity
class InventoryBatch:
    id: Optional[int] = None
    tenant_id: int
    product_id: int
    batch_number: str
    quantity: int
    received_date: date
    expiration_date: Optional[date] = None
    created_by: Optional[int] = None


@entity
class Bottle:
    id: Optional[int] = None
    tenant_id: int
    batch_id: int
    product_id: int
    unique_code: str
    capacity_ml: Decimal
    remaining_ml: Decimal
    initial_weight_g: Optional[Decimal] = None
    status: str = "AVAILABLE"
    installed_slot_id: Optional[int] = None
    installed_at: Optional[datetime] = None


@entity
class InventoryLog:
    id: Optional[int] = None
    tenant_id: int
    bottle_id: int
    action: str
    slot_id: Optional[int] = None
    machine_id: Optional[int] = None
    previous_bottle_id: Optional[int] = None
    quantity_before: Optional[Decimal] = None
    quantity_after: Optional[Decimal] = None
    weight_before: Optional[Decimal] = None
    weight_after: Optional[Decimal] = None
    reason: Optional[str] = None
    order_id: Optional[int] = None
    performed_by: Optional[int] = None
    created_at: Optional[datetime] = None
