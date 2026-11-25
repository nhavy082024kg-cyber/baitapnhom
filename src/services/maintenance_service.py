from datetime import timedelta
from decimal import Decimal
from typing import List, Optional

from domain.clock import utcnow
from domain.constants import (AUTO_TICKET_ALERT_TYPES, ActorType, AlertStatus, DEFAULT_CHECKLISTS, P, Severity,
                              TICKET_DUE_HOURS, TicketCategory, TicketPriority, TicketSeverity, TicketStatus)
from domain.exceptions import BusinessRuleException, ForbiddenException, NotFoundException, ValidationException
from domain.models.irepositories import (IAlertRepository, IMachineRepository, ITicketRepository, IUnitOfWork,
                                         IUserRepository)
from domain.models.maintenance import ChecklistItem, MaintenanceTicket
from domain.models.user import AuthContext
from services.audit_service import AuditService
from services.common import new_code, to_decimal

_VALUES = lambda enum: [e.value for e in enum]          # noqa: E731


class MaintenanceService:
    """
    Ticket lifecycle:  OPEN -> ASSIGNED -> IN_PROGRESS -> AWAITING_TEST -> CLOSED
    A CRITICAL ticket that is not CLOSED blocks new orders on the machine (dispense_policy).
    """

    def __init__(self, tickets: ITicketRepository, machines: IMachineRepository, users: IUserRepository,
                 alerts: IAlertRepository, audit: AuditService, uow: IUnitOfWork, clock=utcnow):
        self.tickets = tickets
        self.machines = machines
        self.users = users
        self.alerts = alerts
        self.audit = audit
        self.uow = uow
        self.clock = clock

    # ------------------------------------------------------------------ manager use cases
    def create_ticket(self, ctx: AuthContext, machine_id: int, category: str, severity: str, title: str,
                      description: Optional[str] = None, priority: str = TicketPriority.NORMAL.value,
                      alert_id: Optional[int] = None, due_at=None) -> MaintenanceTicket:
        ctx.require_permission(P.MAINTENANCE_MANAGE)
        tenant_id = ctx.require_tenant()
        if self.machines.get(tenant_id, machine_id) is None:
            raise NotFoundException("Machine not found")
        if alert_id is not None:
            alert = self.alerts.get(tenant_id, alert_id)
            if alert is None or alert.machine_id != machine_id:
                raise ValidationException("alert_id does not belong to this machine")
            if self.tickets.find_by_alert(alert_id):
                raise BusinessRuleException("This alert already has a ticket", "TICKET_EXISTS")
        ticket = self._new_ticket(tenant_id, machine_id, category, severity, title, description, priority,
                                  alert_id, ctx.user_id, due_at)
        self.audit.record_user(ctx, "TICKET_CREATE", "maintenance_ticket", target_id=ticket.id,
                               after={"ticket_code": ticket.ticket_code, "severity": severity})
        self.uow.commit()
        return ticket

    def assign(self, ctx: AuthContext, ticket_id: int, user_id: int) -> MaintenanceTicket:
        ctx.require_permission(P.MAINTENANCE_MANAGE)
        ticket = self._get(ctx, ticket_id)
        if ticket.status == TicketStatus.CLOSED.value:
            raise BusinessRuleException("Ticket is closed", "TICKET_CLOSED")
        user = self.users.get(user_id)
        if user is None or user.tenant_id != ticket.tenant_id or user.status != "ACTIVE":
            raise ValidationException("The assignee must be an active user of this brand")
        if P.MAINTENANCE_WORK not in self.users.get_permission_codes(user.id):
            raise ValidationException("The assignee has no maintenance permission (technician role needed)")
        before = {"assigned_to": ticket.assigned_to, "status": ticket.status}
        ticket.assigned_to = user.id
        if ticket.status == TicketStatus.OPEN.value:
            ticket.status = TicketStatus.ASSIGNED.value
        self.tickets.update(ticket)
        self.audit.record_user(ctx, "TICKET_ASSIGN", "maintenance_ticket", target_id=ticket.id, before=before,
                               after={"assigned_to": user.id})
        self.uow.commit()
        return ticket

    def list_tickets(self, ctx: AuthContext, status: Optional[str] = None, machine_id: Optional[int] = None,
                     limit: int = 100) -> List[MaintenanceTicket]:
        ctx.require_permission(P.MAINTENANCE_VIEW)
        only_mine = ctx.has_permission(P.MAINTENANCE_WORK) and not ctx.has_permission(P.MAINTENANCE_MANAGE)
        return self.tickets.list(ctx.require_tenant(), status, machine_id,
                                 assigned_to=ctx.user_id if only_mine else None, limit=min(limit, 500))

    def get_ticket(self, ctx: AuthContext, ticket_id: int) -> dict:
        ctx.require_permission(P.MAINTENANCE_VIEW)
        ticket = self._get(ctx, ticket_id)
        self._assert_visible(ctx, ticket)
        return {"ticket": ticket, "checklist": self.tickets.list_items(ticket.id)}

    # ------------------------------------------------------------------ technician use cases
    def start(self, ctx: AuthContext, ticket_id: int) -> MaintenanceTicket:
        ticket = self._work_ticket(ctx, ticket_id)
        if ticket.status not in (TicketStatus.OPEN.value, TicketStatus.ASSIGNED.value):
            raise BusinessRuleException(f"Ticket is {ticket.status}, cannot start", "TICKET_STATE")
        if ticket.assigned_to is None:
            ticket.assigned_to = ctx.user_id
        ticket.status = TicketStatus.IN_PROGRESS.value
        ticket.acknowledged_at = ticket.acknowledged_at or self.clock()
        self.tickets.update(ticket)
        self.audit.record_user(ctx, "TICKET_START", "maintenance_ticket", target_id=ticket.id)
        self.uow.commit()
        return ticket

    def set_checklist_item(self, ctx: AuthContext, ticket_id: int, item_id: int, done: bool = True,
                           note: Optional[str] = None) -> ChecklistItem:
        ticket = self._work_ticket(ctx, ticket_id)
        self._assert_open_for_work(ticket)
        item = self.tickets.get_item(ctx.require_tenant(), item_id)
        if item is None or item.ticket_id != ticket.id:
            raise NotFoundException("Checklist item not found")
        item.is_done = done
        item.note = note
        item.done_by = ctx.user_id if done else None
        item.done_at = self.clock() if done else None
        self.tickets.update_item(item)
        self.uow.commit()
        return item

    def record_result(self, ctx: AuthContext, ticket_id: int, diagnosis: str, corrective_action: str,
                      replaced_parts: Optional[List[str]] = None, cost=None,
                      evidence_urls: Optional[List[str]] = None) -> MaintenanceTicket:
        ticket = self._work_ticket(ctx, ticket_id)
        self._assert_open_for_work(ticket)
        if not (diagnosis or "").strip() or not (corrective_action or "").strip():
            raise ValidationException("diagnosis and corrective_action are required")
        ticket.diagnosis = diagnosis.strip()
        ticket.corrective_action = corrective_action.strip()
        ticket.replaced_parts = replaced_parts or []
        ticket.cost = to_decimal(cost, "cost", Decimal("0")) if cost is not None else None
        ticket.evidence_urls = evidence_urls or []
        self.tickets.update(ticket)
        self.audit.record_user(ctx, "TICKET_RESULT", "maintenance_ticket", target_id=ticket.id,
                               after={"replaced_parts": ticket.replaced_parts, "cost": ticket.cost})
        self.uow.commit()
        return ticket

    def record_post_test(self, ctx: AuthContext, ticket_id: int, passed: bool) -> MaintenanceTicket:
        """The technician states the result of the post-maintenance test (e.g. after a test spray)."""
        ticket = self._work_ticket(ctx, ticket_id)
        self._assert_open_for_work(ticket)
        ticket.post_test_passed = bool(passed)
        ticket.status = TicketStatus.AWAITING_TEST.value if passed else TicketStatus.IN_PROGRESS.value
        self.tickets.update(ticket)
        self.audit.record_user(ctx, "TICKET_POST_TEST", "maintenance_ticket", target_id=ticket.id,
                               after={"passed": bool(passed)})
        self.uow.commit()
        return ticket

    def close(self, ctx: AuthContext, ticket_id: int) -> MaintenanceTicket:
        ticket = self._work_ticket(ctx, ticket_id)
        self._assert_open_for_work(ticket)
        if not ticket.diagnosis or not ticket.corrective_action:
            raise BusinessRuleException("Record the repair result (diagnosis + corrective action) before closing",
                                        "RESULT_REQUIRED")
        pending = [i.item_text for i in self.tickets.list_items(ticket.id) if not i.is_done]
        if pending:
            raise BusinessRuleException(f"Checklist not completed: {pending}", "CHECKLIST_INCOMPLETE")
        if ticket.category == TicketCategory.REPAIR.value and not ticket.post_test_passed:
            raise BusinessRuleException("A successful post-maintenance test is required to close a repair",
                                        "POST_TEST_REQUIRED")
        ticket.status = TicketStatus.CLOSED.value
        ticket.closed_at = self.clock()
        self.tickets.update(ticket)
        if ticket.alert_id:                                  # the problem that raised the ticket is handled
            alert = self.alerts.get(ticket.tenant_id, ticket.alert_id)
            if alert and alert.status != AlertStatus.RESOLVED.value:
                alert.status = AlertStatus.RESOLVED.value
                alert.resolved_by = ctx.user_id
                alert.resolved_at = ticket.closed_at
                alert.resolution_note = f"Ticket {ticket.ticket_code} closed"
                self.alerts.update(alert)
        self.audit.record_user(ctx, "TICKET_CLOSE", "maintenance_ticket", target_id=ticket.id,
                               after={"ticket_code": ticket.ticket_code})
        self.uow.commit()
        return ticket

    # ------------------------------------------------------------------ background job
    def sync_tickets_from_alerts(self) -> int:
        """Open CRITICAL alerts of the configured types get a ticket (once)."""
        created = 0
        for alert in self.alerts.list(None, status=AlertStatus.OPEN.value, limit=500):
            if (alert.severity != Severity.CRITICAL.value or alert.type not in AUTO_TICKET_ALERT_TYPES
                    or self.tickets.find_by_alert(alert.id)):
                continue
            self._new_ticket(alert.tenant_id, alert.machine_id, TicketCategory.REPAIR.value,
                             TicketSeverity.CRITICAL.value, f"{alert.type} on machine {alert.machine_id}",
                             alert.message, TicketPriority.URGENT.value, alert.id, None, None)
            created += 1
        self.uow.commit()
        return created

    # ------------------------------------------------------------------ helpers
    def _new_ticket(self, tenant_id, machine_id, category, severity, title, description, priority, alert_id,
                    created_by, due_at) -> MaintenanceTicket:
        if category not in _VALUES(TicketCategory):
            raise ValidationException("Invalid category")
        if severity not in _VALUES(TicketSeverity):
            raise ValidationException("Invalid severity")
        if priority not in _VALUES(TicketPriority):
            raise ValidationException("Invalid priority")
        now = self.clock()
        ticket = self.tickets.add(MaintenanceTicket(
            tenant_id=tenant_id, ticket_code=new_code("TCK", 8), machine_id=machine_id, category=category,
            severity=severity, priority=priority, status=TicketStatus.OPEN.value, title=title,
            description=description, alert_id=alert_id, created_by=created_by,
            due_at=due_at or now + timedelta(hours=TICKET_DUE_HOURS[severity]), detected_at=now, created_at=now))
        for text in DEFAULT_CHECKLISTS[category]:
            self.tickets.add_item(ChecklistItem(tenant_id=tenant_id, ticket_id=ticket.id, checklist_type=category,
                                                item_text=text))
        return ticket

    def _get(self, ctx: AuthContext, ticket_id: int) -> MaintenanceTicket:
        ticket = self.tickets.get(ctx.require_tenant(), ticket_id)
        if ticket is None:
            raise NotFoundException("Ticket not found")
        return ticket

    def _assert_visible(self, ctx: AuthContext, ticket: MaintenanceTicket) -> None:
        if (not ctx.has_permission(P.MAINTENANCE_MANAGE) and ctx.has_permission(P.MAINTENANCE_WORK)
                and ticket.assigned_to not in (None, ctx.user_id)):
            raise NotFoundException("Ticket not found")      # a technician only sees own tickets

    def _work_ticket(self, ctx: AuthContext, ticket_id: int) -> MaintenanceTicket:
        ctx.require_permission(P.MAINTENANCE_WORK)
        ticket = self._get(ctx, ticket_id)
        if ticket.assigned_to not in (None, ctx.user_id):
            raise ForbiddenException("This ticket is assigned to another technician", "NOT_ASSIGNED")
        return ticket

    @staticmethod
    def _assert_open_for_work(ticket: MaintenanceTicket) -> None:
        if ticket.status in (TicketStatus.OPEN.value, TicketStatus.ASSIGNED.value):
            raise BusinessRuleException("Start the ticket first", "TICKET_NOT_STARTED")
        if ticket.status == TicketStatus.CLOSED.value:
            raise BusinessRuleException("Ticket is closed", "TICKET_CLOSED")
