from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint

from domain.constants import UserStatus
from infrastructure.databases.base import Base
from infrastructure.models.mixins import IdMixin, TimestampMixin, enum_col, fk, id_type


class UserModel(IdMixin, TimestampMixin, Base):
    """ERD 1.2 users (tenant_id NULL = platform user)."""
    __tablename__ = "users"

    tenant_id = fk("tenants.id")
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(150), nullable=False)
    phone = Column(String(30))
    status = enum_col(UserStatus, default=UserStatus.ACTIVE)
    failed_login_count = Column(Integer, nullable=False, default=0)
    last_login_at = Column(DateTime)
    password_reset_token = Column(String(255))
    password_reset_expires_at = Column(DateTime)


class RoleModel(IdMixin, TimestampMixin, Base):
    """ERD 1.3 roles (tenant_id NULL = system role shared by all brands)."""
    __tablename__ = "roles"
    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_roles_tenant_code"),)

    tenant_id = fk("tenants.id")
    code = Column(String(50), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(String(255))
    is_system = Column(Boolean, nullable=False, default=False)


class PermissionModel(IdMixin, TimestampMixin, Base):
    """ERD 1.4 permissions."""
    __tablename__ = "permissions"

    code = Column(String(100), nullable=False, unique=True)
    description = Column(String(255))
    requires_step_up = Column(Boolean, nullable=False, default=False)


class RolePermissionModel(Base):
    """ERD 1.5 role_permissions (composite primary key)."""
    __tablename__ = "role_permissions"

    role_id = Column(id_type(), ForeignKey("roles.id"), primary_key=True)
    permission_id = Column(id_type(), ForeignKey("permissions.id"), primary_key=True)


class UserRoleModel(IdMixin, Base):
    """ERD 1.6 user_roles (optional scope: one location / one machine)."""
    __tablename__ = "user_roles"
    __table_args__ = (UniqueConstraint("user_id", "role_id", "location_id", "machine_id", name="uq_user_roles"),)

    user_id = fk("users.id", nullable=False)
    role_id = fk("roles.id", nullable=False)
    location_id = fk("locations.id")
    machine_id = fk("machines.id")


class UserSessionModel(IdMixin, TimestampMixin, Base):
    """ERD 1.7 user_sessions: one row per issued JWT (jti) so tokens can be revoked."""
    __tablename__ = "user_sessions"

    user_id = fk("users.id", nullable=False)
    token_jti = Column(String(64), nullable=False, unique=True)
    device_info = Column(String(255))
    ip_address = Column(String(45))
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime)
    step_up_verified_until = Column(DateTime)
