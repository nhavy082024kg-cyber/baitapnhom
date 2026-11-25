from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from domain.models.base import entity


@entity
class MaintenanceTicket:
    id: Optional[int] = None
    tenant_id: int
    ticket_code: str
    machine_id: int
    category: str
    severity: str
    priority: str = "NORMAL"
    status: str = "OPEN"
    title: Optional[str] = None
    description: Optional[str] = None
    alert_id: Optional[int] = None
    assigned_to: Optional[int] = None
    created_by: Optional[int] = None
    due_at: Optional[datetime] = None
    diagnosis: Optional[str] = None
    corrective_action: Optional[str] = None
    replaced_parts: Optional[List[str]] = None
    cost: Optional[Decimal] = None
    evidence_urls: Optional[List[str]] = None
    post_test_passed: Optional[bool] = None
    detected_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


@entity
class ChecklistItem:
    id: Optional[int] = None
    tenant_id: int
    ticket_id: int
    checklist_type: str
    item_text: str
    is_done: bool = False
    note: Optional[str] = None
    done_by: Optional[int] = None
    done_at: Optional[datetime] = None
