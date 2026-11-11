# Constants and enums shared by every layer.
# Names are identical to values on purpose (e.g. OrderStatus.PAID == "PAID"),
# so a value read from MySQL can be compared directly with the enum member.

from enum import Enum


class _StrEnum(str, Enum):
    """str-based enum. ALWAYS use `.value` when you assign to an entity/column."""


API_VERSION = "v1"
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
DEFAULT_CURRENCY = "VND"


class RoleCode(_StrEnum):
    SUPER_ADMIN = "SUPER_ADMIN"
    BRAND_ADMIN = "BRAND_ADMIN"
    OPERATIONS_MANAGER = "OPERATIONS_MANAGER"
    TECHNICIAN = "TECHNICIAN"
    INVENTORY_STAFF = "INVENTORY_STAFF"
    VIEWER = "VIEWER"


class TenantStatus(_StrEnum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    INACTIVE = "INACTIVE"


class UserStatus(_StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    LOCKED = "LOCKED"


class LocationStatus(_StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class MachineStatus(_StrEnum):
    ONLINE = "ONLINE"
    UNSTABLE = "UNSTABLE"
    OFFLINE = "OFFLINE"
    MAINTENANCE = "MAINTENANCE"
    DISABLED = "DISABLED"
    ERROR = "ERROR"


class OperatingMode(_StrEnum):
    NORMAL = "NORMAL"
    MAINTENANCE = "MAINTENANCE"
    DISABLED = "DISABLED"


class SlotStatus(_StrEnum):
    AVAILABLE = "AVAILABLE"
    DISABLED = "DISABLED"
    EMPTY = "EMPTY"
    LOW = "LOW"
    ERROR = "ERROR"


class BottleStatus(_StrEnum):
    AVAILABLE = "AVAILABLE"
    INSTALLED = "INSTALLED"
    NEARLY_EMPTY = "NEARLY_EMPTY"
    EMPTY = "EMPTY"
    DAMAGED = "DAMAGED"
    EXPIRED = "EXPIRED"


class InventoryAction(_StrEnum):
    INSTALL = "INSTALL"
    REPLACE = "REPLACE"
    REMOVE = "REMOVE"
    ADJUST = "ADJUST"
    SPRAY_DEDUCT = "SPRAY_DEDUCT"
    TEST_SPRAY = "TEST_SPRAY"
    DISPOSE = "DISPOSE"
    SENSOR_RECONCILE = "SENSOR_RECONCILE"


class PromotionType(_StrEnum):
    FREE_TRIAL = "FREE_TRIAL"
    TEMP_PRICE = "TEMP_PRICE"


class PromotionStatus(_StrEnum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    ENDED = "ENDED"


class OrderStatus(_StrEnum):
    CREATED = "CREATED"
    AWAITING_PAYMENT = "AWAITING_PAYMENT"
    PAID = "PAID"
    DISPENSING = "DISPENSING"
    DISPENSED = "DISPENSED"
    DISPENSE_FAILED = "DISPENSE_FAILED"
    UNCERTAIN = "UNCERTAIN"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    REFUNDED = "REFUNDED"
    MANUAL_REVIEW = "MANUAL_REVIEW"


# Orders that an Operations Manager has to look at (payment succeeded, no spray confirmed)
REVIEW_QUEUE_STATUSES = (
    OrderStatus.DISPENSE_FAILED.value,
    OrderStatus.UNCERTAIN.value,
    OrderStatus.MANUAL_REVIEW.value,
)


class ActorType(_StrEnum):
    SYSTEM = "SYSTEM"
    USER = "USER"
    DEVICE = "DEVICE"
    PAYMENT_PROVIDER = "PAYMENT_PROVIDER"


class PaymentStatus(_StrEnum):
    WAITING = "WAITING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class RefundStatus(_StrEnum):
    REQUESTED = "REQUESTED"
    APPROVED = "APPROVED"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"


class CommandType(_StrEnum):
    SALE = "SALE"
    TEST = "TEST"


class CommandStatus(_StrEnum):
    CREATED = "CREATED"
    SENT = "SENT"
    ACKED = "ACKED"
    EXECUTED = "EXECUTED"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    REJECTED = "REJECTED"


class DeviceEventType(_StrEnum):
    STARTUP = "STARTUP"
    SHUTDOWN = "SHUTDOWN"
    RECONNECT = "RECONNECT"
    MAINTENANCE_MODE = "MAINTENANCE_MODE"
    SENSOR_ERROR = "SENSOR_ERROR"
    DISPENSE_FAILURE = "DISPENSE_FAILURE"
    DOOR_OPEN = "DOOR_OPEN"
    OTHER = "OTHER"


class AlertType(_StrEnum):
    OFFLINE = "OFFLINE"
    LOW_STOCK = "LOW_STOCK"
    EMPTY_SLOT = "EMPTY_SLOT"
    DOOR_OPEN = "DOOR_OPEN"
    LEAKAGE = "LEAKAGE"
    SENSOR_FAILURE = "SENSOR_FAILURE"
    ACTUATOR_FAILURE = "ACTUATOR_FAILURE"
    DISPENSE_FAILURE = "DISPENSE_FAILURE"
    ABNORMAL_CONSUMPTION = "ABNORMAL_CONSUMPTION"
    EXPIRATION = "EXPIRATION"


class Severity(_StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class AlertStatus(_StrEnum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    ASSIGNED = "ASSIGNED"
    RESOLVED = "RESOLVED"
    REOPENED = "REOPENED"


class TicketCategory(_StrEnum):
    INSPECTION = "INSPECTION"
    REPAIR = "REPAIR"
    REFILL_SUPPORT = "REFILL_SUPPORT"
    POST_MAINTENANCE = "POST_MAINTENANCE"


class TicketSeverity(_StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class TicketPriority(_StrEnum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    URGENT = "URGENT"


class TicketStatus(_StrEnum):
    OPEN = "OPEN"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    AWAITING_TEST = "AWAITING_TEST"
    CLOSED = "CLOSED"


class NotificationChannel(_StrEnum):
    IN_APP = "IN_APP"
    EMAIL = "EMAIL"


# --------------------------------------------------------------------------- #
# Permissions (RBAC). Stored in table `permissions`, seeded at start-up.
# --------------------------------------------------------------------------- #
class P:
    TENANT_MANAGE = "platform.tenant.manage"
    PLATFORM_AUDIT = "platform.audit.view"
    JOBS_RUN = "platform.jobs.run"
    USER_MANAGE = "user.manage"
    PRODUCT_MANAGE = "product.manage"
    PRODUCT_VIEW = "product.view"
    LOCATION_MANAGE = "location.manage"
    MACHINE_MANAGE = "machine.manage"
    MACHINE_VIEW = "machine.view"
    MACHINE_CONTROL = "machine.control"          # enable / disable
    MACHINE_MAINTENANCE = "machine.maintenance"  # maintenance mode
    SLOT_CONFIGURE = "slot.configure"
    INVENTORY_MANAGE = "inventory.manage"
    INVENTORY_VIEW = "inventory.view"
    ORDER_VIEW = "order.view"
    ORDER_REFUND = "order.refund"
    ALERT_VIEW = "alert.view"
    ALERT_MANAGE = "alert.manage"
    AUDIT_VIEW = "audit.view"
    DEVICE_TEST_SPRAY = "device.test_spray"


# Sensitive actions: the user must have called POST /auth/step-up recently.
STEP_UP_PERMISSIONS = {P.ORDER_REFUND, P.DEVICE_TEST_SPRAY}

ALL_PERMISSIONS = [v for k, v in vars(P).items() if not k.startswith("_")]

DEFAULT_ROLE_PERMISSIONS = {
    RoleCode.SUPER_ADMIN.value: [
        P.TENANT_MANAGE, P.PLATFORM_AUDIT, P.JOBS_RUN, P.USER_MANAGE,
        P.MACHINE_VIEW, P.AUDIT_VIEW, P.ALERT_VIEW,
    ],
    RoleCode.BRAND_ADMIN.value: [
        P.USER_MANAGE, P.PRODUCT_MANAGE, P.PRODUCT_VIEW, P.LOCATION_MANAGE,
        P.MACHINE_MANAGE, P.MACHINE_VIEW, P.MACHINE_CONTROL, P.MACHINE_MAINTENANCE,
        P.SLOT_CONFIGURE, P.INVENTORY_MANAGE, P.INVENTORY_VIEW, P.ORDER_VIEW,
        P.ALERT_VIEW, P.ALERT_MANAGE, P.AUDIT_VIEW,
    ],
    RoleCode.OPERATIONS_MANAGER.value: [
        P.PRODUCT_VIEW, P.MACHINE_VIEW, P.MACHINE_CONTROL, P.ORDER_VIEW, P.ORDER_REFUND,
        P.INVENTORY_VIEW, P.ALERT_VIEW, P.ALERT_MANAGE,
    ],
    RoleCode.TECHNICIAN.value: [
        P.MACHINE_VIEW, P.MACHINE_MAINTENANCE, P.DEVICE_TEST_SPRAY, P.ALERT_VIEW, P.ALERT_MANAGE,
    ],
    RoleCode.INVENTORY_STAFF.value: [
        P.PRODUCT_VIEW, P.MACHINE_VIEW, P.INVENTORY_MANAGE, P.INVENTORY_VIEW, P.ALERT_VIEW,
    ],
    RoleCode.VIEWER.value: [
        P.PRODUCT_VIEW, P.MACHINE_VIEW, P.ORDER_VIEW, P.INVENTORY_VIEW, P.ALERT_VIEW,
    ],
}
