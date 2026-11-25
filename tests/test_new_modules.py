# Maintenance tickets, promotions, manual stock adjustment, dashboard / CSV / reconciliation.
# Same style as test_business_flows.py: real services + in-memory repositories.

from datetime import timedelta
from decimal import Decimal

import pytest

from domain.constants import ALL_PERMISSIONS, DEFAULT_ROLE_PERMISSIONS
from domain.exceptions import (BusinessRuleException, ForbiddenException, NotFoundException, ValidationException)
from test_business_flows import PW, create_brand, device_cycle, login, pay, w  # noqa: F401  (w = shared fixture)


def make_ticket(w, severity="HIGH", category="REPAIR", **kw):
    return w.maintenance.create_ticket(w.a.ops, w.a.machine.id, category, severity, "Spray is weak", **kw)


def assigned_tech_ctx(w, ticket, email="tech@brand-a.com"):
    tech = login(w, email)
    w.maintenance.assign(w.a.ops, ticket.id, tech.user_id)
    return tech


def finish_checklist(w, tech, ticket):
    for item in w.maintenance.get_ticket(tech, ticket.id)["checklist"]:
        w.maintenance.set_checklist_item(tech, ticket.id, item.id, True, "ok")


def sell_one(w, brand=None, ok=True):
    brand = brand or w.a
    result = w.orders.create_order(brand.device, 1)
    pay(w, result)
    device_cycle(w, brand.device, "EXECUTED" if ok else "FAILED", None if ok else "ACTUATOR")
    return result


# ----------------------------------------------------------------------------- maintenance
def test_ticket_gets_default_checklist_and_due_date(w):
    ticket = make_ticket(w, "CRITICAL")
    detail = w.maintenance.get_ticket(w.a.ops, ticket.id)
    assert ticket.status == "OPEN" and ticket.ticket_code.startswith("TCK")
    assert ticket.due_at == w.clock.now() + timedelta(hours=4)
    assert len(detail["checklist"]) == 4 and not any(i.is_done for i in detail["checklist"])
    assert any(l.action == "TICKET_CREATE" for l in w.repos.audit.search(w.a.tenant.id))


def test_critical_ticket_blocks_orders_until_closed(w):
    ticket = make_ticket(w, "CRITICAL")
    with pytest.raises(BusinessRuleException):
        w.orders.create_order(w.a.device, 1)
    tech = assigned_tech_ctx(w, ticket)
    w.maintenance.start(tech, ticket.id)
    finish_checklist(w, tech, ticket)
    w.maintenance.record_result(tech, ticket.id, "Worn nozzle", "Replaced nozzle", ["nozzle"], "120000")
    w.maintenance.record_post_test(tech, ticket.id, True)
    closed = w.maintenance.close(tech, ticket.id)
    assert closed.status == "CLOSED" and closed.closed_at == w.clock.now()
    assert w.orders.create_order(w.a.device, 1)["order"].status == "AWAITING_PAYMENT"      # sells again


def test_non_critical_ticket_does_not_block_orders(w):
    make_ticket(w, "MEDIUM")
    assert w.orders.create_order(w.a.device, 1)["order"].status == "AWAITING_PAYMENT"


def test_cannot_close_without_result_checklist_and_post_test(w):
    ticket = make_ticket(w)
    tech = assigned_tech_ctx(w, ticket)
    with pytest.raises(BusinessRuleException) as e:                       # must be started first
        w.maintenance.close(tech, ticket.id)
    assert e.value.error_code == "TICKET_NOT_STARTED"
    w.maintenance.start(tech, ticket.id)
    with pytest.raises(BusinessRuleException) as e:
        w.maintenance.close(tech, ticket.id)
    assert e.value.error_code == "RESULT_REQUIRED"
    w.maintenance.record_result(tech, ticket.id, "Clogged", "Cleaned")
    with pytest.raises(BusinessRuleException) as e:
        w.maintenance.close(tech, ticket.id)
    assert e.value.error_code == "CHECKLIST_INCOMPLETE"
    finish_checklist(w, tech, ticket)
    with pytest.raises(BusinessRuleException) as e:                       # a REPAIR needs a passed post-test
        w.maintenance.close(tech, ticket.id)
    assert e.value.error_code == "POST_TEST_REQUIRED"
    w.maintenance.record_post_test(tech, ticket.id, False)                 # failed test: back to IN_PROGRESS
    assert w.repos.tickets.get(w.a.tenant.id, ticket.id).status == "IN_PROGRESS"
    w.maintenance.record_post_test(tech, ticket.id, True)
    assert w.maintenance.close(tech, ticket.id).status == "CLOSED"


def test_inspection_ticket_does_not_need_post_test(w):
    ticket = make_ticket(w, "LOW", "INSPECTION")
    tech = assigned_tech_ctx(w, ticket)
    w.maintenance.start(tech, ticket.id)
    finish_checklist(w, tech, ticket)
    w.maintenance.record_result(tech, ticket.id, "All fine", "None needed")
    assert w.maintenance.close(tech, ticket.id).status == "CLOSED"


def test_closing_a_ticket_resolves_its_alert(w):
    alert = w.alerts.raise_alert(w.a.tenant.id, w.a.machine.id, "ACTUATOR_FAILURE", "CRITICAL", "Pump stuck")
    w.uow.commit()
    ticket = make_ticket(w, "CRITICAL", alert_id=alert.id)
    with pytest.raises(BusinessRuleException):                            # one ticket per alert
        make_ticket(w, "CRITICAL", alert_id=alert.id)
    tech = assigned_tech_ctx(w, ticket)
    w.maintenance.start(tech, ticket.id)
    finish_checklist(w, tech, ticket)
    w.maintenance.record_result(tech, ticket.id, "Pump stuck", "Replaced pump", ["pump"])
    w.maintenance.record_post_test(tech, ticket.id, True)
    w.maintenance.close(tech, ticket.id)
    assert w.repos.alerts.get(w.a.tenant.id, alert.id).status == "RESOLVED"


def test_assignee_must_be_a_technician_of_the_same_brand(w):
    ticket = make_ticket(w)
    with pytest.raises(ValidationException):                              # an operations manager cannot repair
        w.maintenance.assign(w.a.ops, ticket.id, w.a.ops.user_id)
    other = create_brand(w, w.sa, "Brand B", "brand-b")
    with pytest.raises(ValidationException):                              # a technician of another brand
        w.maintenance.assign(w.a.ops, ticket.id, other.tech.user_id)


def test_technician_sees_and_works_only_on_own_tickets(w):
    w.users.create_user(w.a.admin, email="tech2@brand-a.com", password=PW, full_name="Tech 2",
                        role_codes=["TECHNICIAN"])
    mine, theirs = make_ticket(w), make_ticket(w)
    tech1 = assigned_tech_ctx(w, mine)
    tech2 = assigned_tech_ctx(w, theirs, "tech2@brand-a.com")
    assert [t.id for t in w.maintenance.list_tickets(tech1)] == [mine.id]
    assert len(w.maintenance.list_tickets(w.a.ops)) == 2                  # the manager sees everything
    with pytest.raises(NotFoundException):
        w.maintenance.get_ticket(tech1, theirs.id)
    with pytest.raises(ForbiddenException):
        w.maintenance.start(tech1, theirs.id)
    with pytest.raises(ForbiddenException):                               # managers do not do the repair work
        w.maintenance.start(w.a.ops, mine.id)
    assert tech2


def test_ticket_tenant_isolation(w):
    ticket = make_ticket(w)
    other = create_brand(w, w.sa, "Brand B", "brand-b")
    with pytest.raises(NotFoundException):
        w.maintenance.get_ticket(other.ops, ticket.id)
    with pytest.raises(NotFoundException):
        w.maintenance.assign(other.ops, ticket.id, other.tech.user_id)
    with pytest.raises(NotFoundException):                                # machine of another brand
        w.maintenance.create_ticket(other.ops, w.a.machine.id, "REPAIR", "LOW", "x y z")


def test_job_creates_tickets_for_critical_hardware_alerts_once(w):
    w.alerts.raise_alert(w.a.tenant.id, w.a.machine.id, "LEAKAGE", "CRITICAL", "Liquid on the floor")
    w.alerts.raise_alert(w.a.tenant.id, w.a.machine.id, "LOW_STOCK", "CRITICAL", "not a hardware alert", slot_id=1)
    w.alerts.raise_alert(w.a.tenant.id, w.a.machine.id, "SENSOR_FAILURE", "WARNING", "only a warning")
    w.uow.commit()
    assert w.maintenance.sync_tickets_from_alerts() == 1
    assert w.maintenance.sync_tickets_from_alerts() == 0                  # no duplicate on the next run
    ticket = w.maintenance.list_tickets(w.a.ops)[0]
    assert ticket.severity == "CRITICAL" and ticket.priority == "URGENT" and ticket.created_by is None
    with pytest.raises(BusinessRuleException):                            # and the machine stops selling
        w.orders.create_order(w.a.device, 1)


# ----------------------------------------------------------------------------- promotions
def promo(w, **kw):
    data = dict(name="Opening week", type="TEMP_PRICE", temp_price="30000",
                starts_at=(w.clock.now() - timedelta(hours=1)).isoformat(),
                ends_at=(w.clock.now() + timedelta(days=7)).isoformat())
    data.update(kw)
    return w.promotions.create(w.a.admin, **data)


def test_active_promotion_changes_the_price_of_new_orders_only(w):
    before = w.orders.create_order(w.a.device, 1)["order"]
    p = promo(w)
    assert p.status == "DRAFT"
    assert w.orders.create_order(w.a.device, 1)["order"].price == 50000          # a draft does nothing
    w.promotions.activate(w.a.admin, p.id)
    result = w.orders.create_order(w.a.device, 1)
    assert result["order"].price == 30000 and result["order"].promotion_id == p.id
    assert result["payment"].amount == 30000                                     # the customer pays the promo price
    w.promotions.end(w.a.admin, p.id)
    assert w.orders.create_order(w.a.device, 1)["order"].price == 50000
    assert w.repos.orders.get_by_id(before.id).price == 50000                    # old orders keep their price
    assert w.repos.orders.get_by_id(result["order"].id).price == 30000


def test_promotion_scope_and_cheapest_wins(w):
    other_product = w.products.create_product(w.a.admin, {"sku": "oud", "name": "Oud",
                                                          "default_price_per_spray": "70000"})
    w.promotions.activate(w.a.admin, promo(w, product_id=other_product.id, temp_price="1000").id)
    assert w.orders.create_order(w.a.device, 1)["order"].price == 50000          # promotion of another product
    cheap = promo(w, name="Cheap", temp_price="20000", machine_id=w.a.machine.id)
    w.promotions.activate(w.a.admin, w.promotions.create(
        w.a.admin, name="Brand wide", type="TEMP_PRICE", temp_price="35000",
        starts_at=(w.clock.now() - timedelta(hours=1)).isoformat(),
        ends_at=(w.clock.now() + timedelta(days=1)).isoformat()).id)
    w.promotions.activate(w.a.admin, cheap.id)
    assert w.orders.create_order(w.a.device, 1)["order"].price == 20000


def test_promotion_outside_its_dates_does_not_apply(w):
    p = promo(w, starts_at=(w.clock.now() + timedelta(days=1)).isoformat(),
              ends_at=(w.clock.now() + timedelta(days=2)).isoformat())
    w.promotions.activate(w.a.admin, p.id)
    assert w.orders.create_order(w.a.device, 1)["order"].price == 50000
    w.clock.advance(days=1, hours=1)
    w.machines.heartbeat(w.a.device, {})                                       # the machine is still online
    assert w.orders.create_order(w.a.device, 1)["order"].price == 30000


def test_promotion_validation_permissions_and_isolation(w):
    with pytest.raises(ValidationException):
        promo(w, type="FREE_TRIAL")
    with pytest.raises(ValidationException):
        promo(w, temp_price="0")
    with pytest.raises(ValidationException):
        promo(w, ends_at=(w.clock.now() - timedelta(days=1)).isoformat())
    with pytest.raises(ValidationException):
        promo(w, product_id=9999)
    with pytest.raises(ForbiddenException):
        w.promotions.create(w.a.ops, name="x y", type="TEMP_PRICE", temp_price="1000",
                            starts_at="2026-11-07T00:00:00", ends_at="2026-11-09T00:00:00")
    p = promo(w)
    w.promotions.end(w.a.admin, p.id)
    with pytest.raises(BusinessRuleException):                                 # an ENDED promotion cannot be re-activated
        w.promotions.activate(w.a.admin, p.id)
    other = create_brand(w, w.sa, "Brand B", "brand-b")
    with pytest.raises(NotFoundException):
        w.promotions.activate(other.admin, p.id)
    assert w.promotions.list(other.admin) == []


# ----------------------------------------------------------------------------- manual stock adjustment
def step_up(w, email="admin@brand-a.com"):
    token = w.auth.login(email, PW)["token"]
    w.auth.step_up(w.auth.authenticate(token), PW)
    return w.auth.authenticate(token)


def installed_bottle(w):
    return w.repos.inventory.get_bottle(w.a.tenant.id, w.repos.slots.get_by_id(w.a.slots[0].id).current_bottle_id)


def test_adjustment_needs_step_up_and_a_reason(w):
    bottle = installed_bottle(w)
    with pytest.raises(ForbiddenException):
        w.inventory.adjust_bottle(w.a.admin, bottle.id, "2", "weighed it")
    admin = step_up(w)
    with pytest.raises(ValidationException):
        w.inventory.adjust_bottle(admin, bottle.id, "2", "  ")
    with pytest.raises(ValidationException):
        w.inventory.adjust_bottle(admin, bottle.id, "6", "more than capacity")
    with pytest.raises(ForbiddenException):                                     # the technician has no such permission
        w.inventory.adjust_bottle(step_up(w, "tech@brand-a.com"), bottle.id, "2", "weighed it")


def test_adjustment_updates_slot_alerts_log_and_audit(w):
    bottle = installed_bottle(w)
    admin = step_up(w)
    w.inventory.adjust_bottle(admin, bottle.id, "1.5", "Re-weighed on the lab scale")          # 3 sprays left, threshold is 2
    slot = w.repos.slots.get_by_id(w.a.slots[0].id)
    assert slot.estimated_remaining_sprays == 3 and slot.status == "AVAILABLE"
    w.inventory.adjust_bottle(admin, bottle.id, "0.5", "Leak suspected")
    slot = w.repos.slots.get_by_id(w.a.slots[0].id)
    assert slot.estimated_remaining_sprays == 1 and slot.status == "LOW"
    assert [a.type for a in w.repos.alerts.list(w.a.tenant.id)] == ["LOW_STOCK"]
    w.inventory.adjust_bottle(admin, bottle.id, "0", "Bottle emptied by hand")
    assert w.repos.slots.get_by_id(w.a.slots[0].id).status == "EMPTY"
    assert installed_bottle(w).status == "EMPTY"
    w.inventory.adjust_bottle(admin, bottle.id, "5", "Refilled and weighed")
    assert w.repos.slots.get_by_id(w.a.slots[0].id).status == "AVAILABLE"
    assert all(a.status == "RESOLVED" for a in w.repos.alerts.list(w.a.tenant.id))
    logs = [l for l in w.repos.inventory.logs._all() if l.action == "ADJUST"]
    assert len(logs) == 4 and logs[0].reason == "Re-weighed on the lab scale"
    assert logs[0].quantity_before == Decimal("5") and logs[0].quantity_after == Decimal("1.5")
    audit = w.repos.audit.search(w.a.tenant.id, action="INVENTORY_ADJUST")
    assert len(audit) == 4 and audit[0].severity == "WARNING"


def test_adjustment_does_not_touch_other_brands(w):
    other = create_brand(w, w.sa, "Brand B", "brand-b")
    token = w.auth.login("admin@brand-b.com", PW)["token"]
    w.auth.step_up(w.auth.authenticate(token), PW)
    with pytest.raises(NotFoundException):
        w.inventory.adjust_bottle(w.auth.authenticate(token), installed_bottle(w).id, "1", "not mine")
    assert other


# ----------------------------------------------------------------------------- dashboard
def test_dashboard_numbers(w):
    sell_one(w)
    sell_one(w)
    sell_one(w, ok=False)                                                      # paid, machine failed -> review
    w.orders.create_order(w.a.device, 1)                                       # waiting for payment
    data = w.reports.dashboard(w.a.ops)
    assert data["orders"]["total"] == 4
    assert data["orders"]["by_status"]["DISPENSED"] == 2
    assert data["orders"]["paid_not_dispensed"] == 1
    assert data["revenue"]["total"] == 100000 and data["revenue"]["by_day"] == [
        {"date": "2026-11-07", "amount": Decimal("100000")}]
    assert data["dispensing"] == {"success": 2, "attempted": 3, "success_rate": round(2 / 3, 4)}
    assert data["top_products"] == [{"product_id": w.a.product.id, "name": "Rose", "sprays": 2}]
    assert data["machines"] == {"ONLINE": 1}
    assert data["maintenance"]["open_tickets"] == 0


def test_dashboard_low_stock_alerts_and_maintenance_metrics(w):
    for _ in range(8):
        sell_one(w)                                                            # 10 sprays - 8 = 2 left -> LOW
    data = w.reports.dashboard(w.a.ops)
    assert data["low_stock_slots"][0]["slot_number"] == 1 and data["low_stock_slots"][0]["status"] == "LOW"
    assert data["open_alerts"] == {"WARNING": 1}
    ticket = make_ticket(w, "LOW", "INSPECTION")
    tech = assigned_tech_ctx(w, ticket)
    w.maintenance.start(tech, ticket.id)
    finish_checklist(w, tech, ticket)
    w.maintenance.record_result(tech, ticket.id, "Fine", "Nothing")
    w.clock.advance(hours=3)
    w.maintenance.close(tech, ticket.id)
    metrics = w.reports.dashboard(w.a.ops)["maintenance"]
    assert metrics == {"open_tickets": 0, "closed_in_range": 1, "avg_resolution_hours": 3.0}


def test_dashboard_date_range_and_validation(w):
    sell_one(w)
    assert w.reports.dashboard(w.a.ops, "2026-11-07", "2026-11-07")["orders"]["total"] == 1     # whole end day included
    assert w.reports.dashboard(w.a.ops, "2026-10-01", "2026-11-06")["orders"]["total"] == 0
    with pytest.raises(ValidationException):
        w.reports.dashboard(w.a.ops, "2026-11-08", "2026-11-01")
    with pytest.raises(ValidationException):
        w.reports.dashboard(w.a.ops, "2024-01-01", "2026-11-07")                              # more than 366 days
    with pytest.raises(ValidationException):
        w.reports.dashboard(w.a.ops, "not-a-date")


def test_reports_are_scoped_and_permissioned(w):
    sell_one(w)
    other = create_brand(w, w.sa, "Brand B", "brand-b")
    assert w.reports.dashboard(other.ops)["orders"]["total"] == 0              # brand B sees nothing of brand A
    with pytest.raises(ForbiddenException):                                    # a technician has no report access
        w.reports.dashboard(w.a.tech)
    with pytest.raises(ForbiddenException):                                    # the Super Admin has no brand workspace
        w.reports.dashboard(w.sa)
    overview = w.reports.platform_overview(w.sa)
    assert overview["orders"]["dispensed"] == 1 and overview["brands"] == {"ACTIVE": 2}
    assert overview["machines"] == {"ONLINE": 2}
    with pytest.raises(ForbiddenException):                                    # platform reports: Super Admin only
        w.reports.platform_overview(w.a.admin)


# ----------------------------------------------------------------------------- CSV
def test_transactions_csv_content_and_tenant_scope(w):
    done = sell_one(w)
    w.orders.create_order(w.a.device, 1)
    other = create_brand(w, w.sa, "Brand B", "brand-b")
    sell_one(w, other)
    lines = w.reports.export_transactions_csv(w.a.ops).strip().splitlines()
    assert lines[0].startswith("order_code,created_at,machine,product,price,currency,order_status")
    assert len(lines) == 3                                                     # header + 2 own orders
    assert any(done["order"].order_code in l and "DISPENSED" in l and "SUCCESS" in l for l in lines)
    assert not any("brand-b" in l.lower() for l in lines)
    assert w.repos.audit.search(w.a.tenant.id, action="REPORT_EXPORT")
    with pytest.raises(ForbiddenException):
        w.reports.export_transactions_csv(w.a.tech)


def test_csv_blocks_formula_injection(w):
    w.products.update_product(w.a.admin, w.a.product.id, {"name": "=HYPERLINK(\"http://evil\")"})
    sell_one(w)
    csv_text = w.reports.export_transactions_csv(w.a.ops)
    assert "'=HYPERLINK" in csv_text and ",=HYPERLINK" not in csv_text


def test_inventory_csv(w):
    lines = w.reports.export_inventory_csv(w.a.admin).strip().splitlines()
    assert lines[0].startswith("unique_code,product,batch_number")
    assert len(lines) == 2 and "BTL-brand-a" in lines[1] and "INSTALLED" in lines[1]
    other = create_brand(w, w.sa, "Brand B", "brand-b")
    assert "BTL-brand-a" not in w.reports.export_inventory_csv(other.admin)


# ----------------------------------------------------------------------------- reconciliation
def test_reconciliation_matches_flags_and_marks_payments(w):
    ok1, ok2 = sell_one(w), sell_one(w)
    unpaid = w.orders.create_order(w.a.device, 1)
    other = create_brand(w, w.sa, "Brand B", "brand-b")
    foreign = sell_one(w, other)
    ref = lambda r: r["payment"].payment_reference                             # noqa: E731
    records = [
        {"payment_reference": ref(ok1), "amount": "50000", "currency": "VND", "status": "SUCCESS"},
        {"payment_reference": ref(ok2), "amount": "49000", "currency": "VND", "status": "SUCCESS"},     # amount differs
        {"payment_reference": ref(unpaid), "amount": "50000", "currency": "VND", "status": "SUCCESS"},  # we never got paid
        {"payment_reference": ref(foreign), "amount": "50000", "currency": "VND", "status": "SUCCESS"}, # another brand
        {"payment_reference": "SS-UNKNOWN", "amount": "1000", "currency": "VND", "status": "SUCCESS"},
    ]
    result = w.reports.reconcile(w.a.ops, records, "2026-11-07", "2026-11-07")
    assert result["matched"] == [ref(ok1)]
    assert {m["payment_reference"] for m in result["mismatched"]} == {ref(ok2), ref(unpaid)}
    assert ref(foreign) in result["missing_internal"] and "SS-UNKNOWN" in result["missing_internal"]
    assert result["missing_at_provider"] == []
    assert w.repos.payments.get_by_order(ok1["order"].id).reconciled is True
    assert w.repos.payments.get_by_order(ok2["order"].id).reconciled is False
    assert w.repos.payments.get_by_order(foreign["order"].id).reconciled is False      # never touched by brand A
    # the provider forgot a payment we received
    again = w.reports.reconcile(w.a.ops, records[:1], "2026-11-07", "2026-11-07")
    assert again["missing_at_provider"] == [ref(ok2)]
    audit = w.repos.audit.search(w.a.tenant.id, action="PAYMENT_RECONCILE")
    assert len(audit) == 2 and audit[0].severity == "WARNING"


def test_reconciliation_permission_and_input_checks(w):
    with pytest.raises(ForbiddenException):
        w.reports.reconcile(w.a.tech, [], "2026-11-07", "2026-11-07")
    with pytest.raises(ValidationException):                                   # 'from' after 'to'
        w.reports.reconcile(w.a.ops, [], "2026-11-09", "2026-11-01")
    sell_one(w)
    reference = w.repos.payments._all()[0].payment_reference
    with pytest.raises(ValidationException):                                   # amount is not a number
        w.reports.reconcile(w.a.ops, [{"payment_reference": reference, "amount": "abc", "status": "SUCCESS"}],
                            "2026-11-07", "2026-11-07")


# ----------------------------------------------------------------------------- permissions catalogue
def test_every_role_permission_exists_and_new_permissions_are_assigned():
    for role, perms in DEFAULT_ROLE_PERMISSIONS.items():
        assert set(perms) <= set(ALL_PERMISSIONS), role
        assert len(perms) == len(set(perms)), f"duplicate permission in {role}"
    assert len(ALL_PERMISSIONS) == 26
    assert "maintenance.work" in DEFAULT_ROLE_PERMISSIONS["TECHNICIAN"]
    assert "maintenance.work" not in DEFAULT_ROLE_PERMISSIONS["OPERATIONS_MANAGER"]
    assert "inventory.adjust" not in DEFAULT_ROLE_PERMISSIONS["TECHNICIAN"]
    assert "report.view" not in DEFAULT_ROLE_PERMISSIONS["TECHNICIAN"]
