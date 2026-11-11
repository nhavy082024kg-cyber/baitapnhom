# Pure business rules (proposal section 17). No database, no Flask: easy to unit-test.

from datetime import datetime
from decimal import Decimal
from typing import Optional

from domain.constants import MachineStatus, OperatingMode, SlotStatus
from domain.exceptions import BusinessRuleException
from domain.models.catalog import Product
from domain.models.machine import Machine, Slot
from domain.models.settings import ServiceSettings


def connectivity(last_heartbeat_at: Optional[datetime], now: datetime, settings: ServiceSettings) -> str:
    """ONLINE / UNSTABLE / OFFLINE from the age of the last heartbeat."""
    if last_heartbeat_at is None:
        return MachineStatus.OFFLINE.value
    age = (now - last_heartbeat_at).total_seconds()
    if age <= settings.heartbeat_online_seconds:
        return MachineStatus.ONLINE.value
    if age <= settings.heartbeat_unstable_seconds:
        return MachineStatus.UNSTABLE.value
    return MachineStatus.OFFLINE.value


def slot_status_from_stock(remaining_sprays: int, low_threshold: int, disabled: bool = False) -> str:
    if disabled:
        return SlotStatus.DISABLED.value
    if remaining_sprays < 1:
        return SlotStatus.EMPTY.value
    if remaining_sprays <= low_threshold:
        return SlotStatus.LOW.value
    return SlotStatus.AVAILABLE.value


def machine_block_reason(machine: Machine, now: datetime, settings: ServiceSettings) -> Optional[str]:
    """Why the machine cannot sell / dispense right now (None = OK)."""
    if machine.revoked_at is not None:
        return "Machine access has been revoked"
    if machine.operating_mode != OperatingMode.NORMAL.value:
        return f"Machine is in {machine.operating_mode} mode"
    if connectivity(machine.last_heartbeat_at, now, settings) != MachineStatus.ONLINE.value:
        return "Machine is not online"
    return None


def slot_block_reason(slot: Slot) -> Optional[str]:
    if slot.status in (SlotStatus.DISABLED.value, SlotStatus.ERROR.value):
        return f"Slot is {slot.status}"
    if slot.product_id is None or slot.estimated_remaining_sprays < 1 or slot.status == SlotStatus.EMPTY.value:
        return "Slot is empty"
    return None


def assert_can_accept_order(machine: Machine, slot: Optional[Slot], product: Optional[Product],
                            has_critical_ticket: bool, now: datetime, settings: ServiceSettings) -> None:
    """Rules checked when the kiosk creates an order."""
    reason = machine_block_reason(machine, now, settings)
    if reason:
        raise BusinessRuleException(reason, "MACHINE_UNAVAILABLE")
    if has_critical_ticket:
        raise BusinessRuleException("Machine has a critical maintenance ticket", "MACHINE_UNAVAILABLE")
    if slot is None:
        raise BusinessRuleException("Slot does not exist", "SLOT_UNAVAILABLE")
    reason = slot_block_reason(slot)
    if reason:
        raise BusinessRuleException(reason, "SLOT_UNAVAILABLE")
    if product is None or not product.is_available:
        raise BusinessRuleException("Product is not available", "PRODUCT_UNAVAILABLE")
    if slot.price is None or Decimal(slot.price) <= 0:
        raise BusinessRuleException("Slot has no selling price", "SLOT_UNAVAILABLE")
