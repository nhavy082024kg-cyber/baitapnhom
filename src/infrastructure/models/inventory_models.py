from sqlalchemy import Column, Date, DateTime, Integer, Numeric, String, UniqueConstraint

from domain.constants import BottleStatus, InventoryAction
from infrastructure.databases.base import Base
from infrastructure.models.mixins import IdMixin, TimestampMixin, enum_col, fk, id_type


class InventoryBatchModel(IdMixin, TimestampMixin, Base):
    """ERD 1.12 inventory_batches."""
    __tablename__ = "inventory_batches"
    __table_args__ = (UniqueConstraint("tenant_id", "batch_number", name="uq_batches_tenant_number"),)

    tenant_id = fk("tenants.id", nullable=False)
    product_id = fk("products.id", nullable=False)
    batch_number = Column(String(100), nullable=False)
    quantity = Column(Integer, nullable=False)
    received_date = Column(Date, nullable=False)
    expiration_date = Column(Date)
    created_by = fk("users.id")


class BottleModel(IdMixin, TimestampMixin, Base):
    """
    ERD 1.13 bottles / cartridges.
    installed_slot_id is a plain indexed column (no FK): slots.current_bottle_id already references bottles,
    a second FK would make a circular dependency between the two tables.
    """
    __tablename__ = "bottles"

    tenant_id = fk("tenants.id", nullable=False)
    batch_id = fk("inventory_batches.id", nullable=False)
    product_id = fk("products.id", nullable=False)
    unique_code = Column(String(100), nullable=False, unique=True)
    capacity_ml = Column(Numeric(10, 3), nullable=False)       # ERD says (8,2): 3 decimals avoid rounding drift
    initial_weight_g = Column(Numeric(8, 2))
    remaining_ml = Column(Numeric(10, 3), nullable=False)
    status = enum_col(BottleStatus, default=BottleStatus.AVAILABLE)
    installed_slot_id = Column(id_type(), index=True)
    installed_at = Column(DateTime)


class InventoryLogModel(IdMixin, TimestampMixin, Base):
    """ERD 1.14 inventory_logs: install / replace / spray deduction / test spray / adjustment history."""
    __tablename__ = "inventory_logs"

    tenant_id = fk("tenants.id", nullable=False)
    bottle_id = fk("bottles.id", nullable=False)
    slot_id = fk("slots.id")
    machine_id = fk("machines.id")
    action = enum_col(InventoryAction)
    previous_bottle_id = fk("bottles.id")
    quantity_before = Column(Numeric(10, 3))
    quantity_after = Column(Numeric(10, 3))
    weight_before = Column(Numeric(8, 2))
    weight_after = Column(Numeric(8, 2))
    reason = Column(String(255))
    order_id = fk("orders.id")
    performed_by = fk("users.id")
