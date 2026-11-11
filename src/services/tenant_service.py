import re
from typing import List, Optional

from domain.clock import utcnow
from domain.constants import P, TenantStatus
from domain.exceptions import ConflictException, NotFoundException, ValidationException
from domain.models.base import snapshot
from domain.models.irepositories import ISessionRepository, ITenantRepository, IUnitOfWork, IUserRepository
from domain.models.tenant import Tenant
from domain.models.user import AuthContext
from services.audit_service import AuditService


class TenantService:
    """Perfume brands. Only the Platform Super Administrator can use it."""

    def __init__(self, tenants: ITenantRepository, users: IUserRepository, sessions: ISessionRepository,
                 audit: AuditService, uow: IUnitOfWork, clock=utcnow):
        self.tenants = tenants
        self.users = users
        self.sessions = sessions
        self.audit = audit
        self.uow = uow
        self.clock = clock

    def create_tenant(self, ctx: AuthContext, name: str, code: str, description: Optional[str] = None,
                      contact_email: Optional[str] = None, contact_phone: Optional[str] = None,
                      logo_url: Optional[str] = None) -> Tenant:
        ctx.require_permission(P.TENANT_MANAGE)
        code = (code or "").strip().lower()
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{1,48}", code):
            raise ValidationException("code must be 2-49 chars: a-z, 0-9, '-' or '_'")
        if self.tenants.get_by_code(code):
            raise ConflictException("Tenant code already exists")
        tenant = self.tenants.add(Tenant(name=name.strip(), code=code, description=description,
                                         contact_email=contact_email, contact_phone=contact_phone,
                                         logo_url=logo_url, status=TenantStatus.ACTIVE.value))
        self.audit.record_user(ctx, "TENANT_CREATE", "tenant", target_id=tenant.id,
                               after=snapshot(tenant, ["name", "code", "status"]))
        self.uow.commit()
        return tenant

    def list_tenants(self, ctx: AuthContext) -> List[Tenant]:
        ctx.require_permission(P.TENANT_MANAGE)
        return self.tenants.list()

    def get_tenant(self, ctx: AuthContext, tenant_id: int) -> Tenant:
        ctx.require_permission(P.TENANT_MANAGE)
        tenant = self.tenants.get(tenant_id)
        if tenant is None:
            raise NotFoundException("Tenant not found")
        return tenant

    def set_status(self, ctx: AuthContext, tenant_id: int, status: str) -> Tenant:
        tenant = self.get_tenant(ctx, tenant_id)
        if status not in [s.value for s in TenantStatus]:
            raise ValidationException("Invalid status")
        before = snapshot(tenant, ["status"])
        tenant.status = status
        self.tenants.update(tenant)
        if status != TenantStatus.ACTIVE.value:      # suspended brand: kick every user out immediately
            now = self.clock()
            for user in self.users.list_by_tenant(tenant_id):
                self.sessions.revoke_all_for_user(user.id, now)
        self.audit.record_user(ctx, "TENANT_STATUS_CHANGE", "tenant", target_id=tenant_id,
                               before=before, after={"status": status}, severity="WARNING")
        self.uow.commit()
        return tenant
