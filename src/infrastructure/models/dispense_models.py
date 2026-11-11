from sqlalchemy import JSON, Boolean, CHAR, Column, DateTime, Integer, Numeric, String, UniqueConstraint

from domain.constants import CommandStatus, CommandType, DeviceEventType
from infrastructure.databases.base import Base
from infrastructure.models.mixins import IdMixin, TimestampMixin, enum_col, fk


class DispenseCommandModel(IdMixin, TimestampMixin, Base):
    """
    ERD 1.21 dispense_commands.
    UNIQUE(order_id, type): one SALE command per order = one spray per payment.
    Test sprays have order_id NULL (MySQL allows many NULLs in a unique index), so they never collide.
    """
    __tablename__ = "dispense_commands"
    __table_args__ = (UniqueConstraint("order_id", "type", name="uq_command_order_type"),)

    tenant_id = fk("tenants.id", nullable=False)
    command_id = Column(CHAR(36), nullable=False, unique=True)
    order_id = fk("orders.id")
    machine_id = fk("machines.id", nullable=False)
    slot_id = fk("slots.id", nullable=False)
    type = enum_col(CommandType)
    status = enum_col(CommandStatus, default=CommandStatus.CREATED)
    signature = Column(String(255), nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    ack_at = Column(DateTime)
    executed_at = Column(DateTime)
    failure_code = Column(String(50))
    sensor_data = Column(JSON)
    requested_by = fk("users.id")


class DeviceTelemetryModel(IdMixin, TimestampMixin, Base):
    """ERD 1.22 device_telemetry (event_uid UNIQUE: offline re-sync never duplicates)."""
    __tablename__ = "device_telemetry"

    tenant_id = fk("tenants.id", nullable=False)
    machine_id = fk("machines.id", nullable=False)
    slot_id = fk("slots.id")
    event_uid = Column(CHAR(36), nullable=False, unique=True)
    weight_g = Column(Numeric(8, 2))
    estimated_remaining = Column(Integer)
    door_open = Column(Boolean)
    leak_detected = Column(Boolean)
    actuator_state = Column(String(30))
    power_status = Column(String(30))
    recorded_at = Column(DateTime, nullable=False)
    received_at = Column(DateTime, nullable=False)


class DeviceEventModel(IdMixin, TimestampMixin, Base):
    """ERD 1.23 device_events."""
    __tablename__ = "device_events"

    tenant_id = fk("tenants.id", nullable=False)
    machine_id = fk("machines.id", nullable=False)
    event_uid = Column(CHAR(36), nullable=False, unique=True)
    event_type = enum_col(DeviceEventType, default=DeviceEventType.OTHER)
    error_code = Column(String(50))
    payload = Column(JSON)
    recorded_at = Column(DateTime, nullable=False)
    received_at = Column(DateTime, nullable=False)
