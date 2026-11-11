from typing import List, Optional

from domain.clock import utcnow
from domain.constants import ActorType, P
from domain.models.base import to_jsonable
from domain.models.device import AuditLog
from domain.models.irepositories import IAuditRepository
from domain.models.user import AuthContext


class AuditService:
    """
    Append-only trail. record() only adds a row to the CURRENT transaction:
    the calling use case commits, so the audit row and the business change succeed or fail together.
    """

    def __init__(self, repository: IAuditRepository, clock=utcnow):
        self.repository = repository
        self.clock = clock

    def record(self, *, action: str, target_type: str, tenant_id: Optional[int] = None,
               actor_type: str = ActorType.USER.value, actor_id: Optional[int] = None,
               target_id: Optional[int] = None, order_id: Optional[int] = None,
               before: Optional[dict] = None, after: Optional[dict] = None,
               severity: str = "INFO", source_ip: Optional[str] = None) -> None:
        self.repository.add(AuditLog(
            tenant_id=tenant_id, actor_type=actor_type, actor_id=actor_id, action=action,
            target_type=target_type, target_id=target_id, order_id=order_id,
            before_value=to_jsonable(before), after_value=to_jsonable(after),
            severity=severity, source_ip=source_ip, created_at=self.clock(),
        ))

    def record_user(self, ctx: AuthContext, action: str, target_type: str, **kwargs) -> None:
        self.record(action=action, target_type=target_type, tenant_id=ctx.tenant_id,
                    actor_type=ActorType.USER.value, actor_id=ctx.user_id, **kwargs)

    def search(self, ctx: AuthContext, action: Optional[str] = None,
               order_id: Optional[int] = None, limit: int = 100) -> List[AuditLog]:
        # Brand users see only their tenant; the Super Admin sees everything.
        ctx.require_permission(P.PLATFORM_AUDIT if ctx.is_platform else P.AUDIT_VIEW)
        return self.repository.search(ctx.tenant_id, action=action, order_id=order_id, limit=min(limit, 500))
