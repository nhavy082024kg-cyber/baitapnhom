from sqlalchemy import Boolean, Column, DateTime, Numeric, String, Text, UniqueConstraint

from domain.constants import LocationStatus, PromotionStatus, PromotionType
from infrastructure.databases.base import Base
from infrastructure.models.mixins import IdMixin, TimestampMixin, enum_col, fk


class LocationModel(IdMixin, TimestampMixin, Base):
    """ERD 1.8 locations."""
    __tablename__ = "locations"

    tenant_id = fk("tenants.id", nullable=False)
    name = Column(String(150), nullable=False)
    address = Column(String(500))
    city = Column(String(100))
    latitude = Column(Numeric(9, 6))
    longitude = Column(Numeric(9, 6))
    status = enum_col(LocationStatus, default=LocationStatus.ACTIVE)


class ProductModel(IdMixin, TimestampMixin, Base):
    """ERD 1.9 products (perfumes)."""
    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("tenant_id", "sku", name="uq_products_tenant_sku"),)

    tenant_id = fk("tenants.id", nullable=False)
    sku = Column(String(50), nullable=False)
    name = Column(String(150), nullable=False)
    description = Column(Text)
    image_url = Column(String(500))
    top_notes = Column(String(255))
    middle_notes = Column(String(255))
    base_notes = Column(String(255))
    usage_instructions = Column(Text)
    default_price_per_spray = Column(Numeric(12, 2), nullable=False)
    product_qr_url = Column(String(500))
    is_available = Column(Boolean, nullable=False, default=True)


class PromotionModel(IdMixin, TimestampMixin, Base):
    """ERD 1.15 promotions (table ready, no endpoints yet)."""
    __tablename__ = "promotions"

    tenant_id = fk("tenants.id", nullable=False)
    name = Column(String(150), nullable=False)
    type = enum_col(PromotionType)
    temp_price = Column(Numeric(12, 2))
    product_id = fk("products.id")
    machine_id = fk("machines.id")
    location_id = fk("locations.id")
    starts_at = Column(DateTime, nullable=False)
    ends_at = Column(DateTime, nullable=False)
    status = enum_col(PromotionStatus, default=PromotionStatus.DRAFT)
