from sqlalchemy import JSON, Column, DateTime, String

from domain.clock import utcnow
from domain.constants import ActorType, Severity
from infrastructure.databases.base import Base
from infrastructure.models.mixins import IdMixin, TimestampMixin, enum_col, fk, id_type


class AuditLogModel(IdMixin, Base):
    """ERD 1.28 audit_logs: append-only (the repository has no update/delete)."""
    __tablename__ = "audit_logs"

    tenant_id = fk("tenants.id")
    actor_type = enum_col(ActorType, default=ActorType.USER)
    actor_id = Column(id_type())
    action = Column(String(100), nullable=False, index=True)
    target_type = Column(String(50), nullable=False)
    target_id = Column(id_type())
    order_id = Column(id_type(), index=True)          # end-to-end trace: order -> payment -> command -> stock
    before_value = Column(JSON)
    after_value = Column(JSON)
    severity = enum_col(Severity, default=Severity.INFO)
    source_ip = Column(String(45))
    created_at = Column(DateTime, nullable=False, default=utcnow, index=True)


class PlatformSettingModel(IdMixin, TimestampMixin, Base):
    """ERD 1.29 platform_settings (table ready, no endpoints yet)."""
    __tablename__ = "platform_settings"

    setting_key = Column(String(100), nullable=False, unique=True)
    setting_value = Column(JSON, nullable=False)
    updated_by = fk("users.id")
