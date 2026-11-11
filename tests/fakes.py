# In-memory implementations of every repository interface.
# They let us test ALL business logic without MySQL: that is the point of Clean Architecture.
# Like a real DB they return COPIES, so a service that forgets to call update() is caught by the tests.

from copy import deepcopy
from datetime import datetime, timedelta
from types import SimpleNamespace

from domain.constants import DEFAULT_ROLE_PERMISSIONS
from domain.models import irepositories as I
from domain.models.settings import ServiceSettings


class Clock:
    def __init__(self):
        self.current = datetime(2026, 11, 7, 9, 0, 0)

    def now(self):
        return self.current

    def advance(self, **kw):
        self.current += timedelta(**kw)


class UniqueViolation(Exception):
    pass


class Mem:
    def __init__(self):
        self.rows, self.seq = {}, 0

    def _add(self, e):
        self.seq += 1
        e.id = self.seq
        self.rows[e.id] = deepcopy(e)
        return deepcopy(e)

    def _save(self, e):
        self.rows[e.id] = deepcopy(e)
        return deepcopy(e)

    def _all(self):
        return [deepcopy(r) for r in self.rows.values()]

    def _one(self, pred):
        return next((deepcopy(r) for r in self.rows.values() if pred(r)), None)


class UoW(I.IUnitOfWork):
    def __init__(self):
        self.commits = 0

    def commit(self):
        self.commits += 1

    def rollback(self):
        pass


class Tenants(Mem, I.ITenantRepository):
    def add(self, t): return self._add(t)
    def get(self, i): return self._one(lambda r: r.id == i)
    def get_by_code(self, c): return self._one(lambda r: r.code == c)
    def list(self): return self._all()
    def update(self, t): return self._save(t)


class Users(Mem, I.IUserRepository):
    def __init__(self):
        super().__init__()
        self.roles = {}

    def add(self, u, role_codes):
        u = self._add(u)
        self.roles[u.id] = list(role_codes)
        return u

    def get(self, i): return self._one(lambda r: r.id == i)
    def get_by_email(self, e): return self._one(lambda r: r.email == e)
    def list_by_tenant(self, t): return [u for u in self._all() if t is None or u.tenant_id == t]
    def update(self, u): return self._save(u)
    def get_role_codes(self, i): return list(self.roles.get(i, []))

    def get_permission_codes(self, i):
        return {p for r in self.roles.get(i, []) for p in DEFAULT_ROLE_PERMISSIONS[r]}


class Sessions(Mem, I.ISessionRepository):
    def add(self, s): return self._add(s)
    def get_by_jti(self, j): return self._one(lambda r: r.token_jti == j)
    def update(self, s): return self._save(s)

    def revoke_all_for_user(self, uid, at):
        n = 0
        for r in self.rows.values():
            if r.user_id == uid and r.revoked_at is None:
                r.revoked_at, n = at, n + 1
        return n


class Products(Mem, I.IProductRepository):
    def add(self, p): return self._add(p)
    def get(self, t, i): return self._one(lambda r: r.id == i and r.tenant_id == t)
    def list(self, t): return [p for p in self._all() if p.tenant_id == t]
    def update(self, p): return self._save(p)


class Locations(Mem, I.ILocationRepository):
    def add(self, l): return self._add(l)
    def get(self, t, i): return self._one(lambda r: r.id == i and r.tenant_id == t)
    def list(self, t): return [l for l in self._all() if l.tenant_id == t]


class Machines(Mem, I.IMachineRepository):
    def __init__(self):
        super().__init__()
        self.critical_ticket = set()

    def add(self, m): return self._add(m)
    def get(self, t, i): return self._one(lambda r: r.id == i and r.tenant_id == t)
    def get_by_id(self, i): return self._one(lambda r: r.id == i)
    def get_by_serial(self, s): return self._one(lambda r: r.serial_number == s)
    def list(self, t): return [m for m in self._all() if t is None or m.tenant_id == t]
    def update(self, m): return self._save(m)
    def has_critical_open_ticket(self, i): return i in self.critical_ticket


class Slots(Mem, I.ISlotRepository):
    def add(self, s): return self._add(s)
    def get(self, t, i): return self._one(lambda r: r.id == i and r.tenant_id == t)
    def get_by_id(self, i): return self._one(lambda r: r.id == i)
    def get_by_number(self, m, n): return self._one(lambda r: r.machine_id == m and r.slot_number == n)
    def list_by_machine(self, m): return sorted((s for s in self._all() if s.machine_id == m), key=lambda s: s.slot_number)
    def update(self, s): return self._save(s)


class Inventory(I.IInventoryRepository):
    def __init__(self):
        self.batches, self.bottles, self.logs = Mem(), Mem(), Mem()

    def add_batch(self, b): return self.batches._add(b)
    def get_batch(self, t, i): return self.batches._one(lambda r: r.id == i and r.tenant_id == t)
    def list_batches(self, t): return [b for b in self.batches._all() if b.tenant_id == t]
    def add_bottle(self, b): return self.bottles._add(b)
    def get_bottle(self, t, i): return self.bottles._one(lambda r: r.id == i and r.tenant_id == t)
    def get_bottle_by_code(self, t, c): return self.bottles._one(lambda r: r.unique_code == c and r.tenant_id == t)

    def list_bottles(self, t, status=None):
        return [b for b in self.bottles._all() if b.tenant_id == t and (status is None or b.status == status)]

    def update_bottle(self, b): return self.bottles._save(b)
    def add_log(self, l): return self.logs._add(l)


class Orders(Mem, I.IOrderRepository):
    def __init__(self):
        super().__init__()
        self.history = Mem()

    def add(self, o): return self._add(o)
    def get(self, t, i): return self._one(lambda r: r.id == i and r.tenant_id == t)
    def get_by_id(self, i): return self._one(lambda r: r.id == i)
    def get_by_code(self, c): return self._one(lambda r: r.order_code == c)

    def list(self, t, status=None, machine_id=None, limit=100):
        return [o for o in self._all() if o.tenant_id == t and (status is None or o.status == status)
                and (machine_id is None or o.machine_id == machine_id)][:limit]

    def update(self, o): return self._save(o)
    def add_history(self, h): return self.history._add(h)
    def list_history(self, oid): return [h for h in self.history._all() if h.order_id == oid]

    def list_overdue_awaiting_payment(self, now):
        return [o for o in self._all() if o.status == "AWAITING_PAYMENT" and o.expires_at <= now]


class Payments(Mem, I.IPaymentRepository):
    def add(self, p): return self._add(p)
    def get_by_reference(self, r): return self._one(lambda x: x.payment_reference == r)
    def get_by_order(self, i): return self._one(lambda x: x.order_id == i)
    def update(self, p): return self._save(p)


class Webhooks(I.IWebhookEventRepository):
    def __init__(self):
        self.events = {}

    def add_if_new(self, e):
        if e.provider_event_id in self.events:
            return False
        self.events[e.provider_event_id] = deepcopy(e)
        return True

    def mark_processed(self, event_id, payment_id=None):
        self.events[event_id].processed = True


class Refunds(Mem, I.IRefundRepository):
    def add(self, r): return self._add(r)
    def list_by_order(self, i): return [r for r in self._all() if r.order_id == i]


class Commands(Mem, I.IDispenseCommandRepository):
    def add(self, c):
        # mimics UNIQUE(order_id, type) in MySQL
        if c.order_id is not None and any(r.order_id == c.order_id and r.type == c.type for r in self.rows.values()):
            raise UniqueViolation("one command per order")
        return self._add(c)

    def get_by_command_id(self, c): return self._one(lambda r: r.command_id == c)
    def get_sale_for_order(self, i): return self._one(lambda r: r.order_id == i and r.type == "SALE")
    def list_for_order(self, i): return [c for c in self._all() if c.order_id == i]
    def list_open_for_machine(self, m): return [c for c in self._all() if c.machine_id == m and c.status in ("CREATED", "SENT")]

    def list_expired_open(self, now):
        return [c for c in self._all() if c.status in ("CREATED", "SENT", "ACKED") and c.expires_at < now]

    def update(self, c): return self._save(c)


class DeviceData(I.IDeviceDataRepository):
    def __init__(self):
        self.telemetry, self.events = {}, {}

    def add_telemetry_if_new(self, r):
        if r.event_uid in self.telemetry:
            return False
        self.telemetry[r.event_uid] = r
        return True

    def add_event_if_new(self, e):
        if e.event_uid in self.events:
            return False
        self.events[e.event_uid] = e
        return True


class Alerts(Mem, I.IAlertRepository):
    def add(self, a): return self._add(a)
    def get(self, t, i): return self._one(lambda r: r.id == i and r.tenant_id == t)
    def find_open_by_dedup(self, k): return self._one(lambda r: r.dedup_key == k and r.status != "RESOLVED")

    def list(self, t, status=None, limit=100):
        return [a for a in self._all() if (t is None or a.tenant_id == t) and (status is None or a.status == status)][:limit]

    def update(self, a): return self._save(a)


class Audit(Mem, I.IAuditRepository):
    def add(self, l): return self._add(l)

    def search(self, t, action=None, order_id=None, limit=100):
        return [l for l in self._all() if (t is None or l.tenant_id == t) and (action is None or l.action == action)
                and (order_id is None or l.order_id == order_id)][:limit]


def build_world():
    """Wire every service with in-memory repositories (same wiring as dependency_container.py)."""
    from infrastructure.services.payment_provider_service import MockPaymentProvider
    from infrastructure.services.security_service import DeviceSecurity, PasswordHasher, TokenService
    from services.alert_service import AlertService
    from services.audit_service import AuditService
    from services.auth_service import AuthService
    from services.catalog_service import LocationService, ProductService
    from services.dispensing_service import DispensingService
    from services.inventory_service import InventoryService
    from services.machine_service import MachineService
    from services.order_service import OrderService
    from services.order_workflow import OrderWorkflow
    from services.payment_service import PaymentService
    from services.tenant_service import TenantService
    from services.user_service import UserService

    w, clock, settings, uow = SimpleNamespace(), Clock(), ServiceSettings(), UoW()
    r = SimpleNamespace(tenants=Tenants(), users=Users(), sessions=Sessions(), products=Products(),
                        locations=Locations(), machines=Machines(), slots=Slots(), inventory=Inventory(),
                        orders=Orders(), payments=Payments(), webhooks=Webhooks(), refunds=Refunds(),
                        commands=Commands(), device_data=DeviceData(), alerts=Alerts(), audit=Audit())
    hasher, tokens = PasswordHasher(), TokenService("test-secret-key-test-secret-key-123")
    devices, provider = DeviceSecurity("master-key"), MockPaymentProvider("webhook-secret")
    now = clock.now
    audit = AuditService(r.audit, now)
    alerts = AlertService(r.alerts, r.machines, uow, now)
    workflow = OrderWorkflow(r.orders, now)
    inventory = InventoryService(r.inventory, r.slots, r.products, alerts, audit, uow, now)
    dispensing = DispensingService(r.commands, r.orders, r.slots, r.machines, devices, inventory, alerts,
                                   workflow, audit, uow, settings, now)
    w.__dict__.update(
        clock=clock, repos=r, uow=uow, provider=provider, devices=devices, hasher=hasher, alerts=alerts,
        audit=audit, inventory=inventory, dispensing=dispensing, workflow=workflow,
        auth=AuthService(r.users, r.sessions, r.tenants, hasher, tokens, audit, uow, settings, now),
        tenants=TenantService(r.tenants, r.users, r.sessions, audit, uow, now),
        users=UserService(r.users, r.sessions, r.tenants, hasher, audit, uow, now),
        products=ProductService(r.products, audit, uow), locations=LocationService(r.locations, audit, uow),
        machines=MachineService(r.machines, r.slots, r.products, r.locations, r.device_data, devices, alerts,
                                audit, uow, settings, now),
        orders=OrderService(r.orders, r.payments, r.slots, r.products, r.machines, r.refunds, r.commands,
                            provider, workflow, audit, uow, settings, now),
        payments=PaymentService(r.payments, r.orders, r.webhooks, provider, workflow, dispensing, audit, uow, now),
    )
    return w
