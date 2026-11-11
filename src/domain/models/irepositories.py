# Repository interfaces (ports). services/ depends on these, infrastructure/repositories implements them.
# Rule: every method that reads tenant data takes tenant_id -> tenant isolation lives in ONE place.

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional, Set

from domain.models.catalog import Location, Product
from domain.models.device import Alert, AuditLog, DeviceEvent, TelemetryRecord
from domain.models.dispense import DispenseCommand
from domain.models.inventory import Bottle, InventoryBatch, InventoryLog
from domain.models.machine import Machine, Slot
from domain.models.order import Order, OrderStatusHistory, Payment, Refund, WebhookEvent
from domain.models.tenant import Tenant
from domain.models.user import User, UserSession


class IUnitOfWork(ABC):
    """One request = one transaction. Services call commit() once at the end of a use case."""

    @abstractmethod
    def commit(self) -> None: ...

    @abstractmethod
    def rollback(self) -> None: ...


class ITenantRepository(ABC):
    @abstractmethod
    def add(self, tenant: Tenant) -> Tenant: ...

    @abstractmethod
    def get(self, tenant_id: int) -> Optional[Tenant]: ...

    @abstractmethod
    def get_by_code(self, code: str) -> Optional[Tenant]: ...

    @abstractmethod
    def list(self) -> List[Tenant]: ...

    @abstractmethod
    def update(self, tenant: Tenant) -> Tenant: ...


class IUserRepository(ABC):
    @abstractmethod
    def add(self, user: User, role_codes: List[str]) -> User: ...

    @abstractmethod
    def get(self, user_id: int) -> Optional[User]: ...

    @abstractmethod
    def get_by_email(self, email: str) -> Optional[User]: ...

    @abstractmethod
    def list_by_tenant(self, tenant_id: Optional[int]) -> List[User]: ...

    @abstractmethod
    def update(self, user: User) -> User: ...

    @abstractmethod
    def get_role_codes(self, user_id: int) -> List[str]: ...

    @abstractmethod
    def get_permission_codes(self, user_id: int) -> Set[str]: ...


class ISessionRepository(ABC):
    @abstractmethod
    def add(self, session: UserSession) -> UserSession: ...

    @abstractmethod
    def get_by_jti(self, jti: str) -> Optional[UserSession]: ...

    @abstractmethod
    def update(self, session: UserSession) -> UserSession: ...

    @abstractmethod
    def revoke_all_for_user(self, user_id: int, revoked_at: datetime) -> int: ...


class IProductRepository(ABC):
    @abstractmethod
    def add(self, product: Product) -> Product: ...

    @abstractmethod
    def get(self, tenant_id: int, product_id: int) -> Optional[Product]: ...

    @abstractmethod
    def list(self, tenant_id: int) -> List[Product]: ...

    @abstractmethod
    def update(self, product: Product) -> Product: ...


class ILocationRepository(ABC):
    @abstractmethod
    def add(self, location: Location) -> Location: ...

    @abstractmethod
    def get(self, tenant_id: int, location_id: int) -> Optional[Location]: ...

    @abstractmethod
    def list(self, tenant_id: int) -> List[Location]: ...


class IMachineRepository(ABC):
    @abstractmethod
    def add(self, machine: Machine) -> Machine: ...

    @abstractmethod
    def get(self, tenant_id: int, machine_id: int) -> Optional[Machine]: ...

    @abstractmethod
    def get_by_id(self, machine_id: int) -> Optional[Machine]:
        """No tenant filter: only for system flows (device auth, webhook, jobs)."""

    @abstractmethod
    def get_by_serial(self, serial_number: str) -> Optional[Machine]: ...

    @abstractmethod
    def list(self, tenant_id: Optional[int]) -> List[Machine]:
        """tenant_id=None returns every machine (platform users / background jobs only)."""

    @abstractmethod
    def update(self, machine: Machine) -> Machine: ...

    @abstractmethod
    def has_critical_open_ticket(self, machine_id: int) -> bool: ...


class ISlotRepository(ABC):
    @abstractmethod
    def add(self, slot: Slot) -> Slot: ...

    @abstractmethod
    def get(self, tenant_id: int, slot_id: int) -> Optional[Slot]: ...

    @abstractmethod
    def get_by_id(self, slot_id: int) -> Optional[Slot]: ...

    @abstractmethod
    def get_by_number(self, machine_id: int, slot_number: int) -> Optional[Slot]: ...

    @abstractmethod
    def list_by_machine(self, machine_id: int) -> List[Slot]: ...

    @abstractmethod
    def update(self, slot: Slot) -> Slot: ...


class IInventoryRepository(ABC):
    @abstractmethod
    def add_batch(self, batch: InventoryBatch) -> InventoryBatch: ...

    @abstractmethod
    def get_batch(self, tenant_id: int, batch_id: int) -> Optional[InventoryBatch]: ...

    @abstractmethod
    def list_batches(self, tenant_id: int) -> List[InventoryBatch]: ...

    @abstractmethod
    def add_bottle(self, bottle: Bottle) -> Bottle: ...

    @abstractmethod
    def get_bottle(self, tenant_id: int, bottle_id: int) -> Optional[Bottle]: ...

    @abstractmethod
    def get_bottle_by_code(self, tenant_id: int, unique_code: str) -> Optional[Bottle]: ...

    @abstractmethod
    def list_bottles(self, tenant_id: int, status: Optional[str] = None) -> List[Bottle]: ...

    @abstractmethod
    def update_bottle(self, bottle: Bottle) -> Bottle: ...

    @abstractmethod
    def add_log(self, log: InventoryLog) -> InventoryLog: ...


class IOrderRepository(ABC):
    @abstractmethod
    def add(self, order: Order) -> Order: ...

    @abstractmethod
    def get(self, tenant_id: int, order_id: int) -> Optional[Order]: ...

    @abstractmethod
    def get_by_id(self, order_id: int) -> Optional[Order]:
        """No tenant filter: only for system flows (webhook, device result)."""

    @abstractmethod
    def get_by_code(self, order_code: str) -> Optional[Order]: ...

    @abstractmethod
    def list(self, tenant_id: int, status: Optional[str] = None,
             machine_id: Optional[int] = None, limit: int = 100) -> List[Order]: ...

    @abstractmethod
    def update(self, order: Order) -> Order: ...

    @abstractmethod
    def add_history(self, history: OrderStatusHistory) -> OrderStatusHistory: ...

    @abstractmethod
    def list_history(self, order_id: int) -> List[OrderStatusHistory]: ...

    @abstractmethod
    def list_overdue_awaiting_payment(self, now: datetime) -> List[Order]: ...


class IPaymentRepository(ABC):
    @abstractmethod
    def add(self, payment: Payment) -> Payment: ...

    @abstractmethod
    def get_by_reference(self, payment_reference: str) -> Optional[Payment]: ...

    @abstractmethod
    def get_by_order(self, order_id: int) -> Optional[Payment]: ...

    @abstractmethod
    def update(self, payment: Payment) -> Payment: ...


class IWebhookEventRepository(ABC):
    @abstractmethod
    def add_if_new(self, event: WebhookEvent) -> bool:
        """True = stored (first time). False = provider_event_id already known (duplicate webhook)."""

    @abstractmethod
    def mark_processed(self, provider_event_id: str, payment_id: Optional[int] = None) -> None: ...


class IRefundRepository(ABC):
    @abstractmethod
    def add(self, refund: Refund) -> Refund: ...

    @abstractmethod
    def list_by_order(self, order_id: int) -> List[Refund]: ...


class IDispenseCommandRepository(ABC):
    @abstractmethod
    def add(self, command: DispenseCommand) -> DispenseCommand: ...

    @abstractmethod
    def get_by_command_id(self, command_id: str) -> Optional[DispenseCommand]: ...

    @abstractmethod
    def get_sale_for_order(self, order_id: int) -> Optional[DispenseCommand]: ...

    @abstractmethod
    def list_for_order(self, order_id: int) -> List[DispenseCommand]: ...

    @abstractmethod
    def list_open_for_machine(self, machine_id: int) -> List[DispenseCommand]:
        """Commands in CREATED or SENT status (not yet acknowledged by the device)."""

    @abstractmethod
    def list_expired_open(self, now: datetime) -> List[DispenseCommand]:
        """Commands in CREATED / SENT / ACKED whose expires_at < now."""

    @abstractmethod
    def update(self, command: DispenseCommand) -> DispenseCommand: ...


class IDeviceDataRepository(ABC):
    @abstractmethod
    def add_telemetry_if_new(self, record: TelemetryRecord) -> bool: ...

    @abstractmethod
    def add_event_if_new(self, event: DeviceEvent) -> bool: ...


class IAlertRepository(ABC):
    @abstractmethod
    def add(self, alert: Alert) -> Alert: ...

    @abstractmethod
    def get(self, tenant_id: int, alert_id: int) -> Optional[Alert]: ...

    @abstractmethod
    def find_open_by_dedup(self, dedup_key: str) -> Optional[Alert]:
        """An alert with the same dedup_key that is not RESOLVED yet."""

    @abstractmethod
    def list(self, tenant_id: Optional[int], status: Optional[str] = None, limit: int = 100) -> List[Alert]: ...

    @abstractmethod
    def update(self, alert: Alert) -> Alert: ...


class IAuditRepository(ABC):
    """Append-only: there is intentionally NO update() / delete()."""

    @abstractmethod
    def add(self, log: AuditLog) -> AuditLog: ...

    @abstractmethod
    def search(self, tenant_id: Optional[int], action: Optional[str] = None,
               order_id: Optional[int] = None, limit: int = 100) -> List[AuditLog]: ...
