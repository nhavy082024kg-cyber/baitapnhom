import csv
import io
from collections import Counter, defaultdict
from datetime import timedelta
from decimal import Decimal
from typing import Optional

from domain.clock import utcnow
from domain.constants import (AlertStatus, MachineStatus, OperatingMode, OrderStatus, P, PaymentStatus,
                              REVIEW_QUEUE_STATUSES, SlotStatus, TicketStatus)
from domain.exceptions import ValidationException
from domain.models.dispense_policy import connectivity
from domain.models.irepositories import (IAlertRepository, IInventoryRepository, IMachineRepository,
                                         IOrderRepository, IPaymentRepository, IProductRepository, ISlotRepository,
                                         ITenantRepository, ITicketRepository, IUnitOfWork)
from domain.models.machine import Machine
from domain.models.settings import ServiceSettings
from domain.models.user import AuthContext
from services.audit_service import AuditService
from services.common import parse_datetime, to_decimal

MAX_DAYS = 366
MAX_CSV_ROWS = 20000


def csv_safe(value) -> str:
    """Stops spreadsheet formula injection (=, +, -, @ at the start of a cell)."""
    text = "" if value is None else str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@") else text


def live_status(machine: Machine, now, settings: ServiceSettings) -> str:
    if machine.revoked_at is not None or machine.operating_mode == OperatingMode.DISABLED.value:
        return MachineStatus.DISABLED.value
    if machine.operating_mode == OperatingMode.MAINTENANCE.value:
        return MachineStatus.MAINTENANCE.value
    return connectivity(machine.last_heartbeat_at, now, settings)


class ReportService:
    """Read-only dashboards, CSV exports and payment reconciliation (all scoped to the caller's brand)."""

    def __init__(self, orders: IOrderRepository, payments: IPaymentRepository, machines: IMachineRepository,
                 slots: ISlotRepository, products: IProductRepository, tenants: ITenantRepository,
                 inventory: IInventoryRepository, alerts: IAlertRepository, tickets: ITicketRepository,
                 audit: AuditService, uow: IUnitOfWork, settings: ServiceSettings, clock=utcnow):
        self.orders = orders
        self.payments = payments
        self.machines = machines
        self.slots = slots
        self.products = products
        self.tenants = tenants
        self.inventory = inventory
        self.alerts = alerts
        self.tickets = tickets
        self.audit = audit
        self.uow = uow
        self.settings = settings
        self.clock = clock

    # ------------------------------------------------------------------ dashboard (brand)
    def dashboard(self, ctx: AuthContext, start=None, end=None) -> dict:
        ctx.require_permission(P.REPORT_VIEW)
        tenant_id = ctx.require_tenant()
        start_dt, end_dt = self._range(start, end)
        now = self.clock()
        orders = self.orders.list_between(tenant_id, start_dt, end_dt)
        names = {p.id: p.name for p in self.products.list(tenant_id)}
        machines = self.machines.list(tenant_id)

        by_status = Counter(o.status for o in orders)
        dispensed = [o for o in orders if o.status == OrderStatus.DISPENSED.value]
        revenue_by_day = defaultdict(Decimal)
        for o in dispensed:
            revenue_by_day[(o.dispensed_at or o.created_at).date().isoformat()] += Decimal(o.price)
        reached_machine = len(dispensed) + sum(by_status[s] for s in (OrderStatus.DISPENSE_FAILED.value,
                                                                      OrderStatus.UNCERTAIN.value,
                                                                      OrderStatus.MANUAL_REVIEW.value))
        top = Counter(o.product_id for o in dispensed).most_common(5)

        low_slots = []
        for m in machines:
            for s in self.slots.list_by_machine(m.id):
                if s.status in (SlotStatus.LOW.value, SlotStatus.EMPTY.value) and s.product_id:
                    low_slots.append({"machine_id": m.id, "machine": m.name or m.serial_number,
                                      "slot_number": s.slot_number, "status": s.status,
                                      "estimated_remaining_sprays": s.estimated_remaining_sprays})
        open_alerts = [a for a in self.alerts.list(tenant_id, limit=500) if a.status != AlertStatus.RESOLVED.value]
        tickets = self.tickets.list(tenant_id, limit=500)
        resolved = [(t.closed_at - t.detected_at).total_seconds() / 3600 for t in tickets
                    if t.status == TicketStatus.CLOSED.value and t.closed_at and t.detected_at
                    and start_dt <= t.closed_at < end_dt]
        return {
            "range": {"from": start_dt, "to": end_dt},
            "machines": dict(Counter(live_status(m, now, self.settings) for m in machines)),
            "orders": {"total": len(orders), "by_status": dict(by_status),
                       "paid_not_dispensed": sum(by_status[s] for s in REVIEW_QUEUE_STATUSES)},
            "revenue": {"total": sum(Decimal(o.price) for o in dispensed), "currency": "VND",
                        "by_day": [{"date": d, "amount": a} for d, a in sorted(revenue_by_day.items())]},
            "dispensing": {"success": len(dispensed), "attempted": reached_machine,
                           "success_rate": round(len(dispensed) / reached_machine, 4) if reached_machine else None},
            "top_products": [{"product_id": pid, "name": names.get(pid), "sprays": n} for pid, n in top],
            "low_stock_slots": low_slots,
            "open_alerts": dict(Counter(a.severity for a in open_alerts)),
            "maintenance": {"open_tickets": sum(1 for t in tickets if t.status != TicketStatus.CLOSED.value),
                            "closed_in_range": len(resolved),
                            "avg_resolution_hours": round(sum(resolved) / len(resolved), 2) if resolved else None},
        }

    # ------------------------------------------------------------------ platform overview (Super Admin only)
    def platform_overview(self, ctx: AuthContext, start=None, end=None) -> dict:
        ctx.require_permission(P.PLATFORM_AUDIT)
        if not ctx.is_platform:
            raise ValidationException("Platform overview is only for platform users")
        start_dt, end_dt = self._range(start, end)
        now = self.clock()
        orders = self.orders.list_between(None, start_dt, end_dt)
        dispensed = [o for o in orders if o.status == OrderStatus.DISPENSED.value]
        tenants = self.tenants.list()
        return {
            "range": {"from": start_dt, "to": end_dt},
            "brands": dict(Counter(t.status for t in tenants)),
            "machines": dict(Counter(live_status(m, now, self.settings) for m in self.machines.list(None))),
            "orders": {"total": len(orders), "dispensed": len(dispensed),
                       "paid_not_dispensed": sum(1 for o in orders if o.status in REVIEW_QUEUE_STATUSES)},
            "revenue": {"total": sum(Decimal(o.price) for o in dispensed), "currency": "VND"},
            "open_alerts": dict(Counter(a.severity for a in self.alerts.list(None, limit=500)
                                        if a.status != AlertStatus.RESOLVED.value)),
        }

    # ------------------------------------------------------------------ CSV exports
    def export_transactions_csv(self, ctx: AuthContext, start=None, end=None) -> str:
        ctx.require_permission(P.REPORT_VIEW)
        tenant_id = ctx.require_tenant()
        start_dt, end_dt = self._range(start, end)
        orders = self.orders.list_between(tenant_id, start_dt, end_dt)[:MAX_CSV_ROWS]
        payments = {p.order_id: p for p in self.payments.list_between(tenant_id, start_dt, end_dt)}
        names = {p.id: p.name for p in self.products.list(tenant_id)}
        machines = {m.id: (m.name or m.serial_number) for m in self.machines.list(tenant_id)}
        rows = [["order_code", "created_at", "machine", "product", "price", "currency", "order_status",
                 "payment_status", "payment_reference", "paid_at", "reconciled"]]
        for o in orders:
            p = payments.get(o.id)
            rows.append([o.order_code, o.created_at, machines.get(o.machine_id), names.get(o.product_id), o.price,
                         o.currency, o.status, p.status if p else "", p.payment_reference if p else "",
                         p.paid_at if p and p.paid_at else "", p.reconciled if p else ""])
        self.audit.record_user(ctx, "REPORT_EXPORT", "report", after={"report": "transactions", "rows": len(orders)})
        self.uow.commit()
        return self._to_csv(rows)

    def export_inventory_csv(self, ctx: AuthContext) -> str:
        ctx.require_permission(P.REPORT_VIEW)
        tenant_id = ctx.require_tenant()
        names = {p.id: p.name for p in self.products.list(tenant_id)}
        batches = {b.id: b for b in self.inventory.list_batches(tenant_id)}
        rows = [["unique_code", "product", "batch_number", "expiration_date", "capacity_ml", "remaining_ml",
                 "status", "installed_slot_id"]]
        for b in self.inventory.list_bottles(tenant_id)[:MAX_CSV_ROWS]:
            batch = batches.get(b.batch_id)
            rows.append([b.unique_code, names.get(b.product_id), batch.batch_number if batch else "",
                         batch.expiration_date if batch and batch.expiration_date else "", b.capacity_ml,
                         b.remaining_ml, b.status, b.installed_slot_id or ""])
        self.audit.record_user(ctx, "REPORT_EXPORT", "report", after={"report": "inventory", "rows": len(rows) - 1})
        self.uow.commit()
        return self._to_csv(rows)

    # ------------------------------------------------------------------ reconciliation
    def reconcile(self, ctx: AuthContext, records: list, start, end) -> dict:
        """
        Compare our payments with the provider's report.
        records: [{"payment_reference", "amount", "currency", "status"}]  (from the provider's statement).
        """
        ctx.require_permission(P.PAYMENT_RECONCILE)
        tenant_id = ctx.require_tenant()
        start_dt, end_dt = self._range(start, end)
        if len(records) > MAX_CSV_ROWS:
            raise ValidationException("Too many records")
        internal = {p.payment_reference: p for p in self.payments.list_between(tenant_id, start_dt, end_dt)}
        matched, mismatched, missing_internal, seen = [], [], [], set()
        for rec in records:
            reference = str(rec.get("payment_reference", ""))
            payment = internal.get(reference)
            seen.add(reference)
            if payment is None:                      # also covers a reference of another brand: never reveal it
                missing_internal.append(reference)
                continue
            amount = to_decimal(rec.get("amount"), "amount")
            problems = []
            if Decimal(payment.amount) != amount:
                problems.append(f"amount: ours {payment.amount}, provider {amount}")
            if rec.get("currency", payment.currency) != payment.currency:
                problems.append("currency differs")
            if (rec.get("status") == "SUCCESS") != (payment.status == PaymentStatus.SUCCESS.value):
                problems.append(f"status: ours {payment.status}, provider {rec.get('status')}")
            if problems:
                mismatched.append({"payment_reference": reference, "problems": problems})
            else:
                if payment.status == PaymentStatus.SUCCESS.value and not payment.reconciled:
                    payment.reconciled = True
                    self.payments.update(payment)
                matched.append(reference)
        missing_at_provider = [ref for ref, p in internal.items()
                               if p.status == PaymentStatus.SUCCESS.value and ref not in seen]
        result = {"matched": matched, "mismatched": mismatched, "missing_internal": missing_internal,
                  "missing_at_provider": missing_at_provider}
        self.audit.record_user(ctx, "PAYMENT_RECONCILE", "payment",
                               after={k: len(v) for k, v in result.items()},
                               severity="WARNING" if mismatched or missing_internal or missing_at_provider else "INFO")
        self.uow.commit()
        return result

    # ------------------------------------------------------------------ helpers
    def _range(self, start, end):
        end_dt = parse_datetime(end) if end else None
        if end_dt is not None and len(str(end)) <= 10:         # a plain date means "until the end of that day"
            end_dt += timedelta(days=1)
        end_dt = end_dt or self.clock() + timedelta(seconds=1)
        start_dt = parse_datetime(start) if start else end_dt - timedelta(days=30)
        if start_dt >= end_dt:
            raise ValidationException("'from' must be before 'to'")
        if (end_dt - start_dt).days > MAX_DAYS:
            raise ValidationException(f"The range cannot exceed {MAX_DAYS} days")
        return start_dt, end_dt

    @staticmethod
    def _to_csv(rows) -> str:
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        for row in rows:
            writer.writerow([csv_safe(c) for c in row])
        return buffer.getvalue()
