from sqlalchemy import JSON, Boolean, Column, DateTime, Numeric, String, Text

from domain.constants import (AlertStatus, AlertType, NotificationChannel, Severity, TicketCategory,
                              TicketPriority, TicketSeverity, TicketStatus)
from infrastructure.databases.base import Base
from infrastructure.models.mixins import IdMixin, TimestampMixin, enum_col, fk


class AlertModel(IdMixin, TimestampMixin, Base):
    """ERD 1.24 alerts (dedup_key avoids duplicate open alerts for the same problem)."""
    __tablename__ = "alerts"

    tenant_id = fk("tenants.id", nullable=False)
    machine_id = fk("machines.id", nullable=False)
    slot_id = fk("slots.id")
    location_id = fk("locations.id")
    type = enum_col(AlertType)
    severity = enum_col(Severity)
    status = enum_col(AlertStatus, default=AlertStatus.OPEN)
    dedup_key = Column(String(150), nullable=False, index=True)
    message = Column(String(500))
    assigned_to = fk("users.id")
    acknowledged_by = fk("users.id")
    resolved_by = fk("users.id")
    occurred_at = Column(DateTime, nullable=False)
    acknowledged_at = Column(DateTime)
    resolved_at = Column(DateTime)
    resolution_note = Column(Text)


class MaintenanceTicketModel(IdMixin, TimestampMixin, Base):
    """ERD 1.25 maintenance_tickets (table ready, no endpoints yet)."""
    __tablename__ = "maintenance_tickets"

    tenant_id = fk("tenants.id", nullable=False)
    ticket_code = Column(String(40), nullable=False, unique=True)
    machine_id = fk("machines.id", nullable=False)
    alert_id = fk("alerts.id")
    category = enum_col(TicketCategory)
    severity = enum_col(TicketSeverity)
    priority = enum_col(TicketPriority, default=TicketPriority.NORMAL)
    status = enum_col(TicketStatus, default=TicketStatus.OPEN)
    assigned_to = fk("users.id")
    created_by = fk("users.id")
    due_at = Column(DateTime)
    diagnosis = Column(Text)
    corrective_action = Column(Text)
    replaced_parts = Column(JSON)
    cost = Column(Numeric(12, 2))
    evidence_urls = Column(JSON)
    post_test_passed = Column(Boolean)
    detected_at = Column(DateTime)
    acknowledged_at = Column(DateTime)
    closed_at = Column(DateTime)


class MaintenanceChecklistItemModel(IdMixin, TimestampMixin, Base):
    """ERD 1.26 maintenance_checklist_items."""
    __tablename__ = "maintenance_checklist_items"

    tenant_id = fk("tenants.id", nullable=False)
    ticket_id = fk("maintenance_tickets.id", nullable=False)
    checklist_type = enum_col(TicketCategory)
    item_text = Column(String(255), nullable=False)
    is_done = Column(Boolean, nullable=False, default=False)
    note = Column(String(500))
    done_by = fk("users.id")
    done_at = Column(DateTime)


class NotificationModel(IdMixin, TimestampMixin, Base):
    """ERD 1.27 notifications."""
    __tablename__ = "notifications"

    tenant_id = fk("tenants.id")
    user_id = fk("users.id", nullable=False)
    alert_id = fk("alerts.id")
    channel = enum_col(NotificationChannel, default=NotificationChannel.IN_APP)
    title = Column(String(200), nullable=False)
    body = Column(Text)
    is_read = Column(Boolean, nullable=False, default=False)
    sent_at = Column(DateTime)
