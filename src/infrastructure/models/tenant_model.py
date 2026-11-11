from sqlalchemy import JSON, Column, String, Text

from domain.constants import TenantStatus
from infrastructure.databases.base import Base
from infrastructure.models.mixins import IdMixin, TimestampMixin, enum_col


class TenantModel(IdMixin, TimestampMixin, Base):
    """ERD 1.1 tenants = perfume brands."""
    __tablename__ = "tenants"

    name = Column(String(150), nullable=False, unique=True)
    code = Column(String(50), nullable=False, unique=True)
    logo_url = Column(String(500))
    description = Column(Text)
    contact_email = Column(String(255))
    contact_phone = Column(String(30))
    kiosk_display_content = Column(JSON)
    status = enum_col(TenantStatus, default=TenantStatus.ACTIVE)
