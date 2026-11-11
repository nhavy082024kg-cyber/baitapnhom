from sqlalchemy import JSON, Column, DateTime, Integer, Numeric, SmallInteger, String, UniqueConstraint

from domain.constants import MachineStatus, OperatingMode, SlotStatus
from infrastructure.databases.base import Base
from infrastructure.models.mixins import IdMixin, TimestampMixin, enum_col, fk


class MachineModel(IdMixin, TimestampMixin, Base):
    """ERD 1.10 machines (each belongs to exactly one tenant)."""
    __tablename__ = "machines"

    tenant_id = fk("tenants.id", nullable=False)
    location_id = fk("locations.id")
    serial_number = Column(String(100), nullable=False, unique=True)
    device_secret_hash = Column(String(255), nullable=False)
    name = Column(String(150))
    status = enum_col(MachineStatus, default=MachineStatus.OFFLINE)
    operating_mode = enum_col(OperatingMode, default=OperatingMode.NORMAL)
    firmware_version = Column(String(50))
    config_version = Column(Integer, nullable=False, default=1)
    operating_hours = Column(JSON)
    low_stock_threshold_default = Column(Integer)
    last_heartbeat_at = Column(DateTime)
    activated_at = Column(DateTime)
    revoked_at = Column(DateTime)


class SlotModel(IdMixin, TimestampMixin, Base):
    """ERD 1.11 slots (independently controlled; at most one active bottle)."""
    __tablename__ = "slots"
    __table_args__ = (UniqueConstraint("machine_id", "slot_number", name="uq_slots_machine_number"),)

    tenant_id = fk("tenants.id", nullable=False)
    machine_id = fk("machines.id", nullable=False)
    slot_number = Column(SmallInteger, nullable=False)
    product_id = fk("products.id")
    current_bottle_id = fk("bottles.id")
    price = Column(Numeric(12, 2), nullable=False, default=0)
    dosage_ms = Column(Integer, nullable=False, default=300)
    ml_per_spray = Column(Numeric(6, 3), nullable=False, default=0.1)
    low_stock_threshold = Column(Integer, nullable=False, default=20)
    estimated_remaining_sprays = Column(Integer, nullable=False, default=0)
    status = enum_col(SlotStatus, default=SlotStatus.EMPTY)
