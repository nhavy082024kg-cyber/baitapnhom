# Runs the real services with in-memory repositories (tests/fakes.py): no MySQL, no Flask needed.
#   cd scentstation-be && pytest -q

import json
import uuid
from datetime import date
from types import SimpleNamespace

import pytest

from domain.exceptions import (BusinessRuleException, ConflictException, ForbiddenException, InvalidStateTransition,
                               NotFoundException, UnauthorizedException)
from domain.models.order_state_machine import assert_transition
from domain.models.user import User
from fakes import build_world

PW = "Password1!"


def login(w, email, password=PW):
    return w.auth.authenticate(w.auth.login(email, password)["token"])


def create_brand(w, sa, name, code, with_stock=True):
    """Brand + admin + ops + technician + product + machine(4 slots) + installed bottle (10 sprays) + heartbeat."""
    tenant = w.tenants.create_tenant(sa, name, code)
    for email, role in ((f"admin@{code}.com", "BRAND_ADMIN"), (f"ops@{code}.com", "OPERATIONS_MANAGER"),
                        (f"tech@{code}.com", "TECHNICIAN")):
        if role == "BRAND_ADMIN":
            w.users.create_user(sa, email=email, password=PW, full_name=role, role_codes=[role], tenant_id=tenant.id)
        else:
            w.users.create_user(login(w, f"admin@{code}.com"), email=email, password=PW, full_name=role, role_codes=[role])
    admin = login(w, f"admin@{code}.com")
    product = w.products.create_product(admin, {"sku": "rose", "name": "Rose", "default_price_per_spray": "50000"})
    machine, secret = w.machines.register_machine(admin, f"KIOSK-{code}", slot_count=4)
    _, slots = w.machines.get_machine(admin, machine.id)
    w.machines.configure_slot(admin, slots[0].id, {"product_id": product.id, "ml_per_spray": "0.5",
                                                   "low_stock_threshold": 2})
    if with_stock:
        batch = w.inventory.create_batch(admin, product.id, "B1", 3, date(2026, 11, 1), date(2027, 11, 1))
        bottle = w.inventory.register_bottle(admin, batch.id, f"BTL-{code}", "5")      # 5 ml / 0.5 = 10 sprays
        w.inventory.install_bottle(admin, slots[0].id, bottle.id)
    device = w.machines.authenticate_device(f"KIOSK-{code}", secret)
    w.machines.heartbeat(device, {"firmware_version": "1.0.0"})
    return SimpleNamespace(tenant=tenant, admin=admin, ops=login(w, f"ops@{code}.com"),
                           tech=login(w, f"tech@{code}.com"), product=product, machine=machine, slots=slots,
                           device=device, secret=secret)


@pytest.fixture
def w():
    world = build_world()
    world.repos.users.add(User(email="root@scentstation.local", full_name="Root",
                               password_hash=world.hasher.hash(PW)), ["SUPER_ADMIN"])
    world.sa = login(world, "root@scentstation.local")
    world.a = create_brand(world, world.sa, "Brand A", "brand-a")
    return world


def pay(w, order_result, status="SUCCESS", event_id=None, amount=None, currency="VND"):
    body = json.dumps({"event_id": event_id or uuid.uuid4().hex, "status": status, "currency": currency,
                       "payment_reference": order_result["payment"].payment_reference,
                       "amount": str(amount if amount is not None else order_result["payment"].amount)}).encode()
    return w.payments.handle_webhook(body, w.provider.sign(body))


def device_cycle(w, device, result="EXECUTED", failure_code=None):
    command = w.dispensing.poll_commands(device)[0]
    w.dispensing.acknowledge(device, command["command_id"])
    w.dispensing.report_result(device, command["command_id"], result, failure_code)
    return command


def order_state(w, order):
    return w.repos.orders.get_by_id(order.id).status


def history(w, order):
    return [h.to_status for h in w.repos.orders.list_history(order.id)]


# ----------------------------------------------------------------------------- auth / RBAC / tenant isolation
def test_login_lockout_after_five_failures(w):
    for _ in range(5):
        with pytest.raises(UnauthorizedException):
            w.auth.login("admin@brand-a.com", "wrong")
    with pytest.raises(UnauthorizedException):
        w.auth.login("admin@brand-a.com", PW)                      # even the right password: locked


def test_logout_and_deactivation_revoke_sessions(w):
    token = w.auth.login("ops@brand-a.com", PW)["token"]
    ctx = w.auth.authenticate(token)
    w.auth.logout(ctx)
    with pytest.raises(UnauthorizedException):
        w.auth.authenticate(token)
    token2 = w.auth.login("tech@brand-a.com", PW)["token"]
    tech_id = w.auth.authenticate(token2).user_id
    w.users.set_status(w.a.admin, tech_id, "INACTIVE")
    with pytest.raises(UnauthorizedException):
        w.auth.authenticate(token2)


def test_suspended_brand_cannot_login(w):
    token = w.auth.login("ops@brand-a.com", PW)["token"]
    w.tenants.set_status(w.sa, w.a.tenant.id, "SUSPENDED")
    with pytest.raises(UnauthorizedException):
        w.auth.authenticate(token)
    with pytest.raises(UnauthorizedException):
        w.auth.login("ops@brand-a.com", PW)


def test_tenant_isolation(w):
    b = create_brand(w, w.sa, "Brand B", "brand-b")
    assert [p.id for p in w.products.list_products(b.admin)] == [b.product.id]
    assert [m.id for m in w.machines.list_machines(b.admin)] == [b.machine.id]
    with pytest.raises(NotFoundException):
        w.products.get_product(b.admin, w.a.product.id)
    with pytest.raises(NotFoundException):
        w.machines.get_machine(b.admin, w.a.machine.id)
    with pytest.raises(NotFoundException):
        w.machines.set_mode(b.admin, w.a.machine.id, "DISABLED")
    with pytest.raises(NotFoundException):
        w.machines.configure_slot(b.admin, w.a.slots[0].id, {"price": "1"})
    with pytest.raises(NotFoundException):
        w.users.set_status(b.admin, w.a.ops.user_id, "INACTIVE")
    with pytest.raises(NotFoundException):
        w.inventory.install_bottle(b.admin, w.a.slots[0].id, 1)


def test_permissions_and_platform_scope(w):
    with pytest.raises(ForbiddenException):                        # technician cannot create products
        w.products.create_product(w.a.tech, {"sku": "x", "name": "x", "default_price_per_spray": "1"})
    with pytest.raises(ForbiddenException):                        # brand admin cannot create brands
        w.tenants.create_tenant(w.a.admin, "Evil", "evil")
    with pytest.raises(ForbiddenException) as e:                   # super admin has no tenant workspace
        w.products.list_products(w.sa)
    assert e.value.error_code in ("PERMISSION_DENIED", "TENANT_REQUIRED")
    with pytest.raises(ForbiddenException):
        w.users.create_user(w.a.admin, email="x@x.com", password=PW, full_name="x", role_codes=["SUPER_ADMIN"])


# ----------------------------------------------------------------------------- the core flow
def test_happy_path_one_payment_one_spray(w):
    a = w.a
    result = w.orders.create_order(a.device, 1)
    order = result["order"]
    assert order.status == "AWAITING_PAYMENT" and order.price == 50000
    assert pay(w, result)["result"] == "paid"
    assert order_state(w, order) == "DISPENSING"

    command = w.dispensing.poll_commands(a.device)[0]
    expected = w.devices.sign_command(a.secret, command["command_id"], a.machine.serial_number, 1, "SALE",
                                      command["expires_at"].isoformat())
    assert command["signature"] == expected                        # the device can verify it
    w.dispensing.acknowledge(a.device, command["command_id"])
    w.dispensing.report_result(a.device, command["command_id"], "EXECUTED")

    assert history(w, order) == ["CREATED", "AWAITING_PAYMENT", "PAID", "DISPENSING", "DISPENSED"]
    assert w.repos.slots.get_by_id(a.slots[0].id).estimated_remaining_sprays == 9
    deducts = [l for l in w.repos.inventory.logs._all() if l.action == "SPRAY_DEDUCT"]
    assert len(deducts) == 1 and deducts[0].order_id == order.id
    assert w.orders.kiosk_order_status(a.device, order.order_code)["dispense_status"] == "EXECUTED"
    trace = {x.action for x in w.repos.audit._all() if x.order_id == order.id}
    assert {"PAYMENT_WEBHOOK", "DISPENSE_COMMAND_CREATE", "DISPENSE_RESULT"} <= trace   # end-to-end traceability


def test_duplicate_webhook_never_sprays_twice(w):
    result = w.orders.create_order(w.a.device, 1)
    assert pay(w, result, event_id="evt-1")["result"] == "paid"
    assert pay(w, result, event_id="evt-1")["result"] == "duplicate_ignored"      # same event re-sent
    assert pay(w, result, event_id="evt-2")["result"] == "already_paid"           # provider retry, new event id
    assert len(w.repos.commands.list_for_order(result["order"].id)) == 1


def test_bad_signature_and_amount_mismatch(w):
    result = w.orders.create_order(w.a.device, 1)
    body = json.dumps({"event_id": "e", "payment_reference": result["payment"].payment_reference,
                       "amount": "50000", "currency": "VND", "status": "SUCCESS"}).encode()
    with pytest.raises(UnauthorizedException):
        w.payments.handle_webhook(body, "deadbeef")
    with pytest.raises(UnauthorizedException):
        w.payments.handle_webhook(body, None)
    with pytest.raises(BusinessRuleException):
        pay(w, result, amount=1)                                   # underpaid
    with pytest.raises(BusinessRuleException):
        pay(w, result, currency="USD")
    assert order_state(w, result["order"]) == "AWAITING_PAYMENT"
    assert w.repos.commands.list_for_order(result["order"].id) == []
    assert any(x.action == "WEBHOOK_BAD_SIGNATURE" and x.severity == "CRITICAL" for x in w.repos.audit._all())


def test_failed_payment_cancels_order_without_command(w):
    result = w.orders.create_order(w.a.device, 1)
    pay(w, result, status="FAILED")
    assert order_state(w, result["order"]) == "CANCELLED"
    assert w.repos.commands.list_for_order(result["order"].id) == []


def test_dispense_failure_goes_to_review_then_refund_needs_step_up(w):
    a = w.a
    result = w.orders.create_order(a.device, 1)
    order = result["order"]
    pay(w, result)
    device_cycle(w, a.device, "REJECTED", "DOOR_OPEN")
    assert order_state(w, order) == "MANUAL_REVIEW"
    assert history(w, order)[-3:] == ["DISPENSING", "DISPENSE_FAILED", "MANUAL_REVIEW"]
    assert len(w.repos.commands.list_for_order(order.id)) == 1                    # NO automatic second spray
    assert w.dispensing.create_sale_command(w.repos.orders.get_by_id(order.id)).command_id   # idempotent
    assert len(w.repos.commands.list_for_order(order.id)) == 1
    assert w.repos.slots.get_by_id(a.slots[0].id).estimated_remaining_sprays == 10  # nothing deducted
    assert [o.id for o in w.orders.list_orders(a.ops, review_queue=True)] == [order.id]

    with pytest.raises(ForbiddenException) as e:                   # no step-up yet
        w.orders.refund_order(a.ops, order.id, "door was open")
    assert e.value.error_code == "STEP_UP_REQUIRED"
    token = w.auth.login("ops@brand-a.com", PW)["token"]
    ctx = w.auth.authenticate(token)
    with pytest.raises(UnauthorizedException):
        w.auth.step_up(ctx, "wrong password")
    w.auth.step_up(ctx, PW)
    ctx = w.auth.authenticate(token)                               # step-up is stored on THIS session
    with pytest.raises(ForbiddenException):                        # another session of the same user: still locked
        w.orders.refund_order(a.ops, order.id, "x")
    refund = w.orders.refund_order(ctx, order.id, "door was open")
    assert refund.status == "COMPLETED" and refund.amount == 50000
    assert order_state(w, order) == "REFUNDED"
    with pytest.raises(ConflictException):
        w.orders.refund_order(ctx, order.id, "again")
    with pytest.raises(ForbiddenException):                        # brand admin has no refund permission
        w.orders.refund_order(a.admin, order.id, "x")


def test_timeouts_never_create_a_second_command(w):
    a = w.a
    # never acknowledged -> certain failure
    r1 = w.orders.create_order(a.device, 1)
    pay(w, r1)
    w.clock.advance(minutes=5)
    w.machines.heartbeat(a.device, {})
    assert w.dispensing.expire_stale_commands() == 1
    assert history(w, r1["order"])[-3:] == ["DISPENSING", "DISPENSE_FAILED", "MANUAL_REVIEW"]
    # acknowledged but no result -> uncertain
    r2 = w.orders.create_order(a.device, 1)
    pay(w, r2)
    command = w.dispensing.poll_commands(a.device)[0]
    w.dispensing.acknowledge(a.device, command["command_id"])
    w.clock.advance(minutes=5)
    assert w.dispensing.expire_stale_commands() == 1
    assert history(w, r2["order"])[-3:] == ["DISPENSING", "UNCERTAIN", "MANUAL_REVIEW"]
    # late result arrives: order stays in review, truth is recorded, stock deducted
    w.dispensing.report_result(a.device, command["command_id"], "EXECUTED")
    assert order_state(w, r2["order"]) == "MANUAL_REVIEW"
    assert any(x.action == "LATE_DEVICE_RESULT" for x in w.repos.audit._all())
    assert w.repos.slots.get_by_id(a.slots[0].id).estimated_remaining_sprays == 9
    assert len(w.repos.commands.list_for_order(r2["order"].id)) == 1


def test_expired_order_paid_late_is_never_sprayed(w):
    result = w.orders.create_order(w.a.device, 1)
    w.clock.advance(minutes=11)
    w.machines.heartbeat(w.a.device, {})
    assert w.orders.kiosk_order_status(w.a.device, result["order"].order_code)["order"].status == "EXPIRED"
    assert pay(w, result)["result"] == "paid_after_close"
    assert order_state(w, result["order"]) == "MANUAL_REVIEW"
    assert w.repos.commands.list_for_order(result["order"].id) == []


def test_background_expiry_job(w):
    w.orders.create_order(w.a.device, 1)
    w.clock.advance(minutes=11)
    assert w.orders.expire_overdue() == 1


@pytest.mark.parametrize("breaker", ["offline", "maintenance", "ticket", "empty_slot", "unknown_slot", "disabled_slot"])
def test_order_blocked_when_machine_or_slot_unavailable(w, breaker):
    a = w.a
    slot_no = 1
    if breaker == "offline":
        w.clock.advance(minutes=10)
    elif breaker == "maintenance":
        w.machines.set_mode(a.tech, a.machine.id, "MAINTENANCE")
        a.device = w.machines.authenticate_device(a.machine.serial_number, a.secret)
    elif breaker == "ticket":
        w.repos.machines.critical_ticket.add(a.machine.id)
    elif breaker == "empty_slot":
        slot_no = 2
    elif breaker == "unknown_slot":
        slot_no = 9
    elif breaker == "disabled_slot":
        w.machines.configure_slot(a.admin, a.slots[0].id, {"enabled": False})
    with pytest.raises(BusinessRuleException):
        w.orders.create_order(a.device, slot_no)


def test_kiosk_catalog_and_order_ownership(w):
    catalog = w.orders.list_catalog(w.a.device)
    assert catalog["orderable"] and [i["slot"].slot_number for i in catalog["items"]] == [1]
    b = create_brand(w, w.sa, "Brand B", "brand-b")
    order = w.orders.create_order(w.a.device, 1)["order"]
    with pytest.raises(NotFoundException):                          # another kiosk cannot read this order
        w.orders.kiosk_order_status(b.device, order.order_code)


# ----------------------------------------------------------------------------- devices, maintenance, inventory
def test_device_credentials_and_command_ownership(w):
    with pytest.raises(UnauthorizedException):
        w.machines.authenticate_device(w.a.machine.serial_number, "wrong-secret")
    b = create_brand(w, w.sa, "Brand B", "brand-b")
    result = w.orders.create_order(w.a.device, 1)
    pay(w, result)
    command = w.dispensing.poll_commands(w.a.device)[0]
    with pytest.raises(NotFoundException):
        w.dispensing.report_result(b.device, command["command_id"], "EXECUTED")
    w.machines.revoke_device(w.a.admin, w.a.machine.id)
    with pytest.raises(UnauthorizedException):
        w.machines.authenticate_device(w.a.machine.serial_number, w.a.secret)


def test_maintenance_and_test_spray_are_recorded_separately(w):
    a = w.a
    token = w.auth.login("tech@brand-a.com", PW)["token"]
    w.auth.step_up(w.auth.authenticate(token), PW)
    tech = w.auth.authenticate(token)
    with pytest.raises(BusinessRuleException):                      # machine is not in maintenance yet
        w.dispensing.create_test_spray(tech, a.machine.id, 1)
    w.machines.set_mode(a.tech, a.machine.id, "MAINTENANCE")
    with pytest.raises(ForbiddenException):                         # a session without step-up is refused
        w.dispensing.create_test_spray(a.tech, a.machine.id, 1)
    command = w.dispensing.create_test_spray(tech, a.machine.id, 1)
    assert command.type == "TEST" and command.order_id is None
    device = w.machines.authenticate_device(a.machine.serial_number, a.secret)
    device_cycle(w, device)
    actions = [l.action for l in w.repos.inventory.logs._all()]
    assert "TEST_SPRAY" in actions and "SPRAY_DEDUCT" not in actions
    with pytest.raises(BusinessRuleException):
        w.machines.set_mode(tech, a.machine.id, "NORMAL")           # post-maintenance test required
    assert w.machines.set_mode(tech, a.machine.id, "NORMAL", post_test_passed=True).operating_mode == "NORMAL"


def test_low_stock_and_empty_alerts_are_not_duplicated(w):
    a = w.a
    for _ in range(10):
        result = w.orders.create_order(a.device, 1)
        pay(w, result)
        device_cycle(w, a.device)
    alerts = w.repos.alerts._all()
    assert [x.type for x in alerts].count("LOW_STOCK") == 1         # raised once at <= 2 sprays, not per spray
    assert [x.type for x in alerts].count("EMPTY_SLOT") == 1
    assert w.repos.slots.get_by_id(a.slots[0].id).status == "EMPTY"
    with pytest.raises(BusinessRuleException):
        w.orders.create_order(a.device, 1)


def test_install_bottle_rules(w):
    a = w.a
    other = w.products.create_product(a.admin, {"sku": "oud", "name": "Oud", "default_price_per_spray": "70000"})
    batch = w.inventory.create_batch(a.admin, other.id, "B2", 1, date(2026, 11, 1))
    bottle = w.inventory.register_bottle(a.admin, batch.id, "OUD-1", "5")
    with pytest.raises(BusinessRuleException) as e:
        w.inventory.install_bottle(a.admin, a.slots[0].id, bottle.id)
    assert e.value.error_code == "WRONG_SCENT"
    with pytest.raises(ForbiddenException):
        w.inventory.install_bottle(a.tech, a.slots[0].id, bottle.id)
    # replacing the installed bottle frees the old one
    batch2 = w.inventory.create_batch(a.admin, a.product.id, "B3", 1, date(2026, 11, 1))
    new_bottle = w.inventory.register_bottle(a.admin, batch2.id, "ROSE-2", "5")
    w.inventory.install_bottle(a.admin, a.slots[0].id, new_bottle.id)
    assert [l.action for l in w.repos.inventory.logs._all()][-1] == "REPLACE"
    assert w.repos.inventory.get_bottle(a.tenant.id, 1).status == "AVAILABLE"
    with pytest.raises(BusinessRuleException):                      # changing perfume with a bottle inside
        w.machines.configure_slot(a.admin, a.slots[0].id, {"product_id": other.id})


def test_price_change_is_audited_and_order_price_is_frozen(w):
    result = w.orders.create_order(w.a.device, 1)
    w.machines.configure_slot(w.a.admin, w.a.slots[0].id, {"price": "99000"})
    assert w.repos.orders.get_by_id(result["order"].id).price == 50000          # fixed at creation
    log = [x for x in w.repos.audit._all() if x.action == "PRICE_CHANGE" and x.target_type == "slot"][-1]
    assert log.before_value["price"] == "50000" and log.after_value["price"] == "99000"


def test_heartbeat_offline_detection_and_idempotent_telemetry(w):
    a = w.a
    payload = {"telemetry": [{"event_uid": "t1", "slot_number": 1, "door_open": True}],
               "events": [{"event_uid": "e1", "event_type": "SENSOR_ERROR", "error_code": "LC-01"}]}
    w.machines.heartbeat(a.device, payload)
    w.machines.heartbeat(a.device, payload)                         # offline re-sync: same uids again
    types = [x.type for x in w.repos.alerts._all()]
    assert types.count("DOOR_OPEN") == 1 and types.count("SENSOR_FAILURE") == 1
    assert len(w.repos.device_data.telemetry) == 1
    w.machines.heartbeat(a.device, {"telemetry": [{"event_uid": "t2", "door_open": False}]})
    assert w.repos.alerts.find_open_by_dedup(f"DOOR_OPEN:{a.machine.id}:0") is None

    w.clock.advance(minutes=10)
    assert w.machines.list_machines(a.admin)[0].status == "OFFLINE"
    assert w.machines.refresh_connectivity() >= 1
    assert w.repos.alerts.find_open_by_dedup(f"OFFLINE:{a.machine.id}:0") is not None
    w.machines.heartbeat(a.device, {})
    assert w.repos.alerts.find_open_by_dedup(f"OFFLINE:{a.machine.id}:0") is None   # recovered


def test_audit_is_tenant_scoped(w):
    b = create_brand(w, w.sa, "Brand B", "brand-b")
    mine = w.audit.search(b.admin)
    assert mine and all(x.tenant_id == b.tenant.id for x in mine)
    assert {x.tenant_id for x in w.audit.search(w.sa)} >= {w.a.tenant.id, b.tenant.id}
    with pytest.raises(ForbiddenException):
        w.audit.search(b.tech)


def test_state_machine_rejects_illegal_transitions():
    for current, target in (("DISPENSED", "PAID"), ("AWAITING_PAYMENT", "DISPENSING"), ("REFUNDED", "PAID"),
                            ("EXPIRED", "DISPENSING"), ("CREATED", "PAID")):
        with pytest.raises(InvalidStateTransition):
            assert_transition(current, target)
    assert_transition("PAID", "DISPENSING")
