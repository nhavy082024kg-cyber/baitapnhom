from datetime import date
from decimal import Decimal
from typing import List, Optional

from domain.clock import utcnow
from domain.constants import AlertType, BottleStatus, InventoryAction, P, Severity, SlotStatus
from domain.exceptions import BusinessRuleException, ConflictException, NotFoundException, ValidationException
from domain.models.dispense_policy import slot_status_from_stock
from domain.models.inventory import Bottle, InventoryBatch, InventoryLog
from domain.models.irepositories import IInventoryRepository, IProductRepository, ISlotRepository, IUnitOfWork
from domain.models.machine import Slot
from domain.models.user import AuthContext
from services.alert_service import AlertService
from services.audit_service import AuditService
from services.common import to_decimal


class InventoryService:
    """Batches, bottles/cartridges, installation in a slot and stock deduction after each spray."""

    def __init__(self, inventory: IInventoryRepository, slots: ISlotRepository, products: IProductRepository,
                 alerts: AlertService, audit: AuditService, uow: IUnitOfWork, clock=utcnow):
        self.inventory = inventory
        self.slots = slots
        self.products = products
        self.alerts = alerts
        self.audit = audit
        self.uow = uow
        self.clock = clock

    # ------------------------------------------------------------------ portal use cases
    def create_batch(self, ctx: AuthContext, product_id: int, batch_number: str, quantity: int,
                     received_date: date, expiration_date: Optional[date] = None) -> InventoryBatch:
        ctx.require_permission(P.INVENTORY_MANAGE)
        tenant_id = ctx.require_tenant()
        if self.products.get(tenant_id, product_id) is None:
            raise ValidationException("Unknown product")
        if quantity < 1:
            raise ValidationException("quantity must be >= 1")
        if expiration_date and expiration_date < received_date:
            raise ValidationException("expiration_date is before received_date")
        if any(b.batch_number == batch_number for b in self.inventory.list_batches(tenant_id)):
            raise ConflictException("Batch number already exists")
        batch = self.inventory.add_batch(InventoryBatch(
            tenant_id=tenant_id, product_id=product_id, batch_number=batch_number, quantity=quantity,
            received_date=received_date, expiration_date=expiration_date, created_by=ctx.user_id))
        self.audit.record_user(ctx, "BATCH_CREATE", "inventory_batch", target_id=batch.id,
                               after={"batch_number": batch_number, "quantity": quantity})
        self.uow.commit()
        return batch

    def list_batches(self, ctx: AuthContext) -> List[InventoryBatch]:
        ctx.require_permission(P.INVENTORY_VIEW)
        return self.inventory.list_batches(ctx.require_tenant())

    def register_bottle(self, ctx: AuthContext, batch_id: int, unique_code: str, capacity_ml,
                        initial_weight_g=None) -> Bottle:
        ctx.require_permission(P.INVENTORY_MANAGE)
        tenant_id = ctx.require_tenant()
        batch = self.inventory.get_batch(tenant_id, batch_id)
        if batch is None:
            raise NotFoundException("Batch not found")
        if self.inventory.get_bottle_by_code(tenant_id, unique_code):
            raise ConflictException("Bottle code already registered")
        capacity = to_decimal(capacity_ml, "capacity_ml", Decimal("0.1"))
        bottle = self.inventory.add_bottle(Bottle(
            tenant_id=tenant_id, batch_id=batch.id, product_id=batch.product_id, unique_code=unique_code,
            capacity_ml=capacity, remaining_ml=capacity, status=BottleStatus.AVAILABLE.value,
            initial_weight_g=to_decimal(initial_weight_g, "initial_weight_g") if initial_weight_g is not None else None))
        self.audit.record_user(ctx, "BOTTLE_REGISTER", "bottle", target_id=bottle.id,
                               after={"unique_code": unique_code, "batch_id": batch.id})
        self.uow.commit()
        return bottle

    def list_bottles(self, ctx: AuthContext, status: Optional[str] = None) -> List[Bottle]:
        ctx.require_permission(P.INVENTORY_VIEW)
        return self.inventory.list_bottles(ctx.require_tenant(), status)

    def install_bottle(self, ctx: AuthContext, slot_id: int, bottle_id: int,
                       weight_before=None, weight_after=None) -> Slot:
        """Put a bottle into a slot (or replace the current one). Verifies the scent matches the slot."""
        ctx.require_permission(P.INVENTORY_MANAGE)
        tenant_id = ctx.require_tenant()
        slot = self.slots.get(tenant_id, slot_id)
        bottle = self.inventory.get_bottle(tenant_id, bottle_id)
        if slot is None or bottle is None:
            raise NotFoundException("Slot or bottle not found")
        if bottle.status != BottleStatus.AVAILABLE.value:
            raise BusinessRuleException(f"Bottle is {bottle.status}, only AVAILABLE bottles can be installed", "BOTTLE_STATE")
        if slot.product_id is None or slot.product_id != bottle.product_id:
            raise BusinessRuleException("Wrong fragrance for this slot", "WRONG_SCENT")
        batch = self.inventory.get_batch(tenant_id, bottle.batch_id)
        if batch and batch.expiration_date and batch.expiration_date < self.clock().date():
            raise BusinessRuleException("Bottle is expired", "BOTTLE_EXPIRED")

        now = self.clock()
        previous_id = slot.current_bottle_id
        if previous_id:                                      # replacement: the old bottle leaves the slot
            previous = self.inventory.get_bottle(tenant_id, previous_id)
            previous.installed_slot_id = None
            previous.installed_at = None
            previous.status = (BottleStatus.EMPTY.value if previous.remaining_ml < slot.ml_per_spray
                               else BottleStatus.AVAILABLE.value)
            self.inventory.update_bottle(previous)

        bottle.status = BottleStatus.INSTALLED.value
        bottle.installed_slot_id = slot.id
        bottle.installed_at = now
        self.inventory.update_bottle(bottle)

        slot.current_bottle_id = bottle.id
        slot.estimated_remaining_sprays = int(bottle.remaining_ml // slot.ml_per_spray)
        slot.status = slot_status_from_stock(slot.estimated_remaining_sprays, slot.low_stock_threshold,
                                             slot.status == SlotStatus.DISABLED.value)
        self.slots.update(slot)

        self.inventory.add_log(InventoryLog(
            tenant_id=tenant_id, bottle_id=bottle.id, slot_id=slot.id, machine_id=slot.machine_id,
            action=InventoryAction.REPLACE.value if previous_id else InventoryAction.INSTALL.value,
            previous_bottle_id=previous_id, quantity_after=bottle.remaining_ml,
            weight_before=to_decimal(weight_before, "weight_before") if weight_before is not None else None,
            weight_after=to_decimal(weight_after, "weight_after") if weight_after is not None else None,
            performed_by=ctx.user_id, created_at=now))
        self.alerts.resolve_by_key(AlertType.EMPTY_SLOT.value, slot.machine_id, slot.id, "Bottle installed")
        self.alerts.resolve_by_key(AlertType.LOW_STOCK.value, slot.machine_id, slot.id, "Bottle installed")
        self.audit.record_user(ctx, "BOTTLE_INSTALL", "slot", target_id=slot.id,
                               after={"bottle_id": bottle.id, "previous_bottle_id": previous_id})
        self.uow.commit()
        return slot

    # ------------------------------------------------------------------ internal (no commit)
    def deduct_spray(self, slot: Slot, order_id: Optional[int] = None, test: bool = False,
                     performed_by: Optional[int] = None) -> Slot:
        """
        One spray happened. Customer sprays are logged as SPRAY_DEDUCT (linked to the order),
        technician test sprays as TEST_SPRAY (never mixed with sales).
        """
        bottle = self.inventory.get_bottle(slot.tenant_id, slot.current_bottle_id) if slot.current_bottle_id else None
        before = bottle.remaining_ml if bottle else None
        if bottle:
            bottle.remaining_ml = max(Decimal("0"), bottle.remaining_ml - slot.ml_per_spray)

        slot.estimated_remaining_sprays = max(0, slot.estimated_remaining_sprays - 1)
        slot.status = slot_status_from_stock(slot.estimated_remaining_sprays, slot.low_stock_threshold,
                                             slot.status == SlotStatus.DISABLED.value)
        self.slots.update(slot)

        if bottle:
            if slot.estimated_remaining_sprays == 0:
                bottle.status = BottleStatus.EMPTY.value
            elif slot.status == SlotStatus.LOW.value:
                bottle.status = BottleStatus.NEARLY_EMPTY.value
            self.inventory.update_bottle(bottle)
            self.inventory.add_log(InventoryLog(
                tenant_id=slot.tenant_id, bottle_id=bottle.id, slot_id=slot.id, machine_id=slot.machine_id,
                action=InventoryAction.TEST_SPRAY.value if test else InventoryAction.SPRAY_DEDUCT.value,
                quantity_before=before, quantity_after=bottle.remaining_ml, order_id=order_id,
                performed_by=performed_by, created_at=self.clock()))

        if slot.estimated_remaining_sprays == 0:
            self.alerts.raise_alert(slot.tenant_id, slot.machine_id, AlertType.EMPTY_SLOT.value,
                                    Severity.CRITICAL.value, f"Slot {slot.slot_number} is empty", slot_id=slot.id)
        elif slot.status == SlotStatus.LOW.value:
            self.alerts.raise_alert(slot.tenant_id, slot.machine_id, AlertType.LOW_STOCK.value,
                                    Severity.WARNING.value,
                                    f"Slot {slot.slot_number}: {slot.estimated_remaining_sprays} sprays left",
                                    slot_id=slot.id)
        return slot
