from datetime import datetime
from decimal import Decimal
from typing import Optional

from domain.models.base import entity


@entity
class Machine:
    id: Optional[int] = None
    tenant_id: int
    serial_number: str
    device_secret_hash: str
    location_id: Optional[int] = None
    name: Optional[str] = None
    status: str = "OFFLINE"
    operating_mode: str = "NORMAL"
    firmware_version: Optional[str] = None
    config_version: int = 1
    low_stock_threshold_default: Optional[int] = None
    last_heartbeat_at: Optional[datetime] = None
    activated_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


@entity
class Slot:
    id: Optional[int] = None
    tenant_id: int
    machine_id: int
    slot_number: int
    product_id: Optional[int] = None
    current_bottle_id: Optional[int] = None
    price: Decimal = Decimal("0")
    dosage_ms: int = 300                       # calibrated spray duration
    ml_per_spray: Decimal = Decimal("0.100")   # calibrated consumption
    low_stock_threshold: int = 20              # remaining sprays
    estimated_remaining_sprays: int = 0
    status: str = "EMPTY"
