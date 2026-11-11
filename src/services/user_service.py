from typing import List, Optional

from domain.clock import utcnow
from domain.constants import P, RoleCode, UserStatus
from domain.exceptions import (BusinessRuleException, ConflictException, ForbiddenException,
                               NotFoundException, ValidationException)
from domain.models.irepositories import ISessionRepository, ITenantRepository, IUnitOfWork, IUserRepository
from domain.models.iservices import IPasswordHasher
from domain.models.user import AuthContext, User
from services.audit_service import AuditService


class UserService:
    def __init__(self, users: IUserRepository, sessions: ISessionRepository, tenants: ITenantRepository,
                 hasher: IPasswordHasher, audit: AuditService, uow: IUnitOfWork, clock=utcnow):
        self.users = users
        self.sessions = sessions
        self.tenants = tenants
        self.hasher = hasher
        self.audit = audit
        self.uow = uow
        self.clock = clock

    def create_user(self, ctx: AuthContext, *, email: str, password: str, full_name: str,
                    role_codes: List[str], tenant_id: Optional[int] = None, phone: Optional[str] = None) -> User:
        ctx.require_permission(P.USER_MANAGE)
        if ctx.tenant_id is None:                       # Super Admin creates a Brand Admin for a given brand
            if tenant_id is None:
                raise ValidationException("tenant_id is required")
            if self.tenants.get(tenant_id) is None:
                raise NotFoundException("Tenant not found")
            target_tenant = tenant_id
        else:                                           # brand users can only create users in their own brand
            if tenant_id not in (None, ctx.tenant_id):
                raise ForbiddenException("Cannot create users for another brand", "TENANT_MISMATCH")
            target_tenant = ctx.tenant_id

        valid = {r.value for r in RoleCode}
        if not role_codes or any(r not in valid for r in role_codes):
            raise ValidationException(f"role_codes must be a non-empty subset of {sorted(valid)}")
        if RoleCode.SUPER_ADMIN.value in role_codes:
            raise ForbiddenException("SUPER_ADMIN cannot be assigned through the API", "ROLE_NOT_ALLOWED")
        if len(password or "") < 8:
            raise ValidationException("Password must have at least 8 characters")

        email = email.strip().lower()
        if self.users.get_by_email(email):
            raise ConflictException("Email already exists")
        user = self.users.add(User(tenant_id=target_tenant, email=email, full_name=full_name.strip(),
                                   phone=phone, password_hash=self.hasher.hash(password),
                                   status=UserStatus.ACTIVE.value), sorted(set(role_codes)))
        self.audit.record_user(ctx, "USER_CREATE", "user", target_id=user.id,
                               after={"email": email, "roles": sorted(set(role_codes)), "tenant_id": target_tenant})
        self.uow.commit()
        return user

    def list_users(self, ctx: AuthContext) -> List[User]:
        ctx.require_permission(P.USER_MANAGE)
        return self.users.list_by_tenant(ctx.tenant_id)

    def set_status(self, ctx: AuthContext, user_id: int, status: str) -> User:
        ctx.require_permission(P.USER_MANAGE)
        if status not in [s.value for s in UserStatus]:
            raise ValidationException("Invalid status")
        user = self.users.get(user_id)
        if user is None or (ctx.tenant_id is not None and user.tenant_id != ctx.tenant_id):
            raise NotFoundException("User not found")          # never reveal users of another brand
        if user.id == ctx.user_id:
            raise BusinessRuleException("You cannot change your own status", "SELF_CHANGE")
        before = {"status": user.status}
        user.status = status
        if status == UserStatus.ACTIVE.value:
            user.failed_login_count = 0
        self.users.update(user)
        if status != UserStatus.ACTIVE.value:               # disabled account -> every session ends now
            self.sessions.revoke_all_for_user(user.id, self.clock())
        self.audit.record_user(ctx, "USER_STATUS_CHANGE", "user", target_id=user.id,
                               before=before, after={"status": status}, severity="WARNING")
        self.uow.commit()
        return user
