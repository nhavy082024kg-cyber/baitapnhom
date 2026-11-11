from datetime import datetime
from typing import Optional

from domain.models.base import entity


@entity
class DispenseCommand:
    id: Optional[int] = None
    tenant_id: int
    command_id: str                      # UUID the device sees
    machine_id: int
    slot_id: int
    type: str = "SALE"                   # SALE | TEST
    status: str = "CREATED"
    signature: str = ""
    expires_at: datetime
    order_id: Optional[int] = None       # None for TEST sprays
    ack_at: Optional[datetime] = None
    executed_at: Optional[datetime] = None
    failure_code: Optional[str] = None
    sensor_data: Optional[dict] = None
    requested_by: Optional[int] = None
    created_at: Optional[datetime] = None
