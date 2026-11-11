# Import every model so Base.metadata knows ALL 29 tables before create_all() / Alembic autogenerate.
from infrastructure.models.tenant_model import TenantModel  # noqa: F401
from infrastructure.models.user_models import (PermissionModel, RoleModel, RolePermissionModel,  # noqa: F401
                                               UserModel, UserRoleModel, UserSessionModel)
from infrastructure.models.catalog_models import LocationModel, ProductModel, PromotionModel  # noqa: F401
from infrastructure.models.machine_models import MachineModel, SlotModel  # noqa: F401
from infrastructure.models.inventory_models import (BottleModel, InventoryBatchModel,  # noqa: F401
                                                    InventoryLogModel)
from infrastructure.models.order_models import (OrderModel, OrderStatusHistoryModel, PaymentModel,  # noqa: F401
                                                PaymentWebhookEventModel, RefundModel)
from infrastructure.models.dispense_models import (DeviceEventModel, DeviceTelemetryModel,  # noqa: F401
                                                   DispenseCommandModel)
from infrastructure.models.alert_models import (AlertModel, MaintenanceChecklistItemModel,  # noqa: F401
                                                MaintenanceTicketModel, NotificationModel)
from infrastructure.models.audit_models import AuditLogModel, PlatformSettingModel  # noqa: F401
