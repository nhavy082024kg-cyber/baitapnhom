from datetime import datetime
from decimal import Decimal
from typing import Optional

from domain.models.base import entity


@entity
class TelemetryRecord:
    id: Optional[int] = None
    tenant_id: int
    machine_id: int
    event_uid: str                       # unique -> offline re-sync never duplicates
    recorded_at: datetime
    received_at: datetime
    slot_id: Optional[int] = None
    weight_g: Optional[Decimal] = None
    estimated_remaining: Optional[int] = None
    door_open: Optional[bool] = None
    leak_detected: Optional[bool] = None
    actuator_state: Optional[str] = None
    power_status: Optional[str] = None


@entity
class DeviceEvent:
    id: Optional[int] = None
    tenant_id: int
    machine_id: int
    event_uid: str
    event_type: str = "OTHER"
    recorded_at: datetime
    received_at: datetime
    error_code: Optional[str] = None
    payload: Optional[dict] = None


@entity
class Alert:
    id: Optional[int] = None
    tenant_id: int
    machine_id: int
    type: str
    severity: str
    status: str = "OPEN"
    dedup_key: str
    occurred_at: datetime
    slot_id: Optional[int] = None
    location_id: Optional[int] = None
    message: Optional[str] = None
    assigned_to: Optional[int] = None
    acknowledged_by: Optional[int] = None
    resolved_by: Optional[int] = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    resolution_note: Optional[str] = None


@entity
class AuditLog:
    id: Optional[int] = None
    tenant_id: Optional[int] = None
    actor_type: str = "USER"
    actor_id: Optional[int] = None
    action: str
    target_type: str
    target_id: Optional[int] = None
    order_id: Optional[int] = None
    before_value: Optional[dict] = None
    after_value: Optional[dict] = None
    severity: str = "INFO"
    source_ip: Optional[str] = None
    created_at: Optional[datetime] = None
