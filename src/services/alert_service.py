from typing import List, Optional

from domain.clock import utcnow
from domain.constants import AlertStatus, P
from domain.exceptions import NotFoundException
from domain.models.device import Alert
from domain.models.irepositories import IAlertRepository, IMachineRepository, IUnitOfWork
from domain.models.user import AuthContext


class AlertService:
    def __init__(self, alerts: IAlertRepository, machines: IMachineRepository, uow: IUnitOfWork, clock=utcnow):
        self.alerts = alerts
        self.machines = machines
        self.uow = uow
        self.clock = clock

    @staticmethod
    def make_key(alert_type: str, machine_id: int, slot_id: Optional[int] = None) -> str:
        return f"{alert_type}:{machine_id}:{slot_id or 0}"

    # ---- internal helpers: do NOT commit, they run inside another use case ---------------
    def raise_alert(self, tenant_id: int, machine_id: int, alert_type: str, severity: str,
                    message: Optional[str] = None, slot_id: Optional[int] = None) -> Alert:
        """Create an alert unless an unresolved alert with the same key already exists (no spam)."""
        key = self.make_key(alert_type, machine_id, slot_id)
        existing = self.alerts.find_open_by_dedup(key)
        if existing:
            return existing
        machine = self.machines.get_by_id(machine_id)
        return self.alerts.add(Alert(
            tenant_id=tenant_id, machine_id=machine_id, slot_id=slot_id,
            location_id=machine.location_id if machine else None, type=alert_type,
            severity=severity, status=AlertStatus.OPEN.value, dedup_key=key,
            message=message, occurred_at=self.clock(),
        ))

    def resolve_by_key(self, alert_type: str, machine_id: int, slot_id: Optional[int] = None,
                       note: str = "Condition cleared automatically") -> None:
        alert = self.alerts.find_open_by_dedup(self.make_key(alert_type, machine_id, slot_id))
        if alert:
            alert.status = AlertStatus.RESOLVED.value
            alert.resolved_at = self.clock()
            alert.resolution_note = note
            self.alerts.update(alert)

    # ---- use cases ------------------------------------------------------------------------
    def list_alerts(self, ctx: AuthContext, status: Optional[str] = None, limit: int = 100) -> List[Alert]:
        ctx.require_permission(P.ALERT_VIEW)
        return self.alerts.list(ctx.tenant_id, status=status, limit=min(limit, 500))

    def acknowledge(self, ctx: AuthContext, alert_id: int) -> Alert:
        ctx.require_permission(P.ALERT_MANAGE)
        alert = self._get(ctx, alert_id)
        if alert.status in (AlertStatus.OPEN.value, AlertStatus.REOPENED.value):
            alert.status = AlertStatus.ACKNOWLEDGED.value
            alert.acknowledged_by = ctx.user_id
            alert.acknowledged_at = self.clock()
            self.alerts.update(alert)
            self.uow.commit()
        return alert

    def resolve(self, ctx: AuthContext, alert_id: int, note: Optional[str] = None) -> Alert:
        ctx.require_permission(P.ALERT_MANAGE)
        alert = self._get(ctx, alert_id)
        if alert.status != AlertStatus.RESOLVED.value:
            alert.status = AlertStatus.RESOLVED.value
            alert.resolved_by = ctx.user_id
            alert.resolved_at = self.clock()
            alert.resolution_note = note
            self.alerts.update(alert)
            self.uow.commit()
        return alert

    def _get(self, ctx: AuthContext, alert_id: int) -> Alert:
        alert = self.alerts.get(ctx.require_tenant(), alert_id)
        if not alert:
            raise NotFoundException("Alert not found")
        return alert
