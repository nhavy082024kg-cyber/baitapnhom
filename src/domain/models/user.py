from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Set

from domain.exceptions import ForbiddenException
from domain.models.base import entity


@entity
class User:
    id: Optional[int] = None
    tenant_id: Optional[int] = None          # None = platform user (Super Admin)
    email: str
    password_hash: str
    full_name: str
    phone: Optional[str] = None
    status: str = "ACTIVE"
    failed_login_count: int = 0
    last_login_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


@entity
class UserSession:
    id: Optional[int] = None
    user_id: int
    token_jti: str
    expires_at: datetime
    ip_address: Optional[str] = None
    device_info: Optional[str] = None
    revoked_at: Optional[datetime] = None
    step_up_verified_until: Optional[datetime] = None


@dataclass
class AuthContext:
    """Who is calling. Built from the JWT on every request, never stored in the DB."""
    user_id: int
    tenant_id: Optional[int]
    email: str
    roles: List[str] = field(default_factory=list)
    permissions: Set[str] = field(default_factory=set)
    jti: str = ""
    step_up_verified_until: Optional[datetime] = None

    @property
    def is_platform(self) -> bool:
        return self.tenant_id is None

    def has_permission(self, code: str) -> bool:
        return code in self.permissions

    def require_permission(self, code: str) -> None:
        if code not in self.permissions:
            raise ForbiddenException(f"Missing permission: {code}", "PERMISSION_DENIED")

    def require_tenant(self) -> int:
        """Tenant-scoped operations: platform users have no tenant and cannot call them."""
        if self.tenant_id is None:
            raise ForbiddenException("This action belongs to a brand workspace", "TENANT_REQUIRED")
        return self.tenant_id

    def require_step_up(self, now: datetime) -> None:
        if not self.step_up_verified_until or self.step_up_verified_until <= now:
            raise ForbiddenException("Re-enter your password (POST /auth/step-up) first", "STEP_UP_REQUIRED")
