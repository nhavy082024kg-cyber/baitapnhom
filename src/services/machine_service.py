from decimal import Decimal
from typing import List, Optional, Tuple

from domain.clock import utcnow
from domain.constants import (AlertType, DeviceEventType, MachineStatus, OperatingMode, P, Severity, SlotStatus)
from domain.exceptions import (BusinessRuleException, ConflictException, ForbiddenException, NotFoundException,
                               UnauthorizedException, ValidationException)
from domain.models.base import snapshot
from domain.models.device import DeviceEvent, TelemetryRecord
from domain.models.dispense_policy import connectivity, slot_status_from_stock
from domain.models.irepositories import (IDeviceDataRepository, ILocationRepository, IMachineRepository,
                                         IProductRepository, ISlotRepository, IUnitOfWork)
from domain.models.iservices import IDeviceSecurity
from domain.models.machine import Machine, Slot
from domain.models.settings import ServiceSettings
from domain.models.user import AuthContext
from services.alert_service import AlertService
from services.audit_service import AuditService
from services.common import parse_datetime, to_decimal

SLOT_WATCHED = ["product_id", "price", "dosage_ms", "ml_per_spray", "low_stock_threshold", "status"]


class MachineService:
    def __init__(self, machines: IMachineRepository, slots: ISlotRepository, products: IProductRepository,
                 locations: ILocationRepository, device_data: IDeviceDataRepository, devices: IDeviceSecurity,
                 alerts: AlertService, audit: AuditService, uow: IUnitOfWork,
                 settings: ServiceSettings, clock=utcnow):
        self.machines = machines
        self.slots = slots
        self.products = products
        self.locations = locations
        self.device_data = device_data
        self.devices = devices
        self.alerts = alerts
        self.audit = audit
        self.uow = uow
        self.settings = settings
        self.clock = clock

    # ------------------------------------------------------------------ management (portal)
    def register_machine(self, ctx: AuthContext, serial_number: str, name: Optional[str] = None,
                         location_id: Optional[int] = None, slot_count: int = 4) -> Tuple[Machine, str]:
        """Returns (machine, device_secret). The secret is shown ONCE: flash it into the kiosk."""
        ctx.require_permission(P.MACHINE_MANAGE)
        tenant_id = ctx.require_tenant()
        serial_number = serial_number.strip()
        if not 1 <= slot_count <= 12:
            raise ValidationException("slot_count must be between 1 and 12")
        if self.machines.get_by_serial(serial_number):
            raise ConflictException("Serial number is already registered")
        if location_id is not None and self.locations.get(tenant_id, location_id) is None:
            raise ValidationException("Unknown location")
        secret = self.devices.derive_secret(serial_number)
        machine = self.machines.add(Machine(
            tenant_id=tenant_id, serial_number=serial_number, name=name, location_id=location_id,
            device_secret_hash=self.devices.hash_secret(secret), status=MachineStatus.OFFLINE.value,
            activated_at=self.clock()))
        for number in range(1, slot_count + 1):
            self.slots.add(Slot(tenant_id=tenant_id, machine_id=machine.id, slot_number=number))
        self.audit.record_user(ctx, "MACHINE_REGISTER", "machine", target_id=machine.id,
                               after={"serial_number": serial_number, "slots": slot_count})
        self.uow.commit()
        return machine, secret

    def list_machines(self, ctx: AuthContext) -> List[Machine]:
        ctx.require_permission(P.MACHINE_VIEW)
        machines = self.machines.list(ctx.tenant_id)
        return [self._with_live_status(m) for m in machines]

    def get_machine(self, ctx: AuthContext, machine_id: int) -> Tuple[Machine, List[Slot]]:
        ctx.require_permission(P.MACHINE_VIEW)
        machine = self._get_machine(ctx, machine_id)
        return self._with_live_status(machine), self.slots.list_by_machine(machine.id)

    def set_mode(self, ctx: AuthContext, machine_id: int, mode: str, post_test_passed: bool = False) -> Machine:
        if mode not in [m.value for m in OperatingMode]:
            raise ValidationException("Invalid mode")
        if not (ctx.has_permission(P.MACHINE_CONTROL) or ctx.has_permission(P.MACHINE_MAINTENANCE)):
            raise ForbiddenException("Missing permission: machine.control", "PERMISSION_DENIED")
        machine = self._get_machine(ctx, machine_id)
        leaving_maintenance = machine.operating_mode == OperatingMode.MAINTENANCE.value and mode != machine.operating_mode
        if mode == OperatingMode.MAINTENANCE.value or leaving_maintenance:
            ctx.require_permission(P.MACHINE_MAINTENANCE)
        else:
            ctx.require_permission(P.MACHINE_CONTROL)
        if leaving_maintenance and mode == OperatingMode.NORMAL.value and not post_test_passed:
            raise BusinessRuleException("A successful post-maintenance test is required before returning to service",
                                        "POST_TEST_REQUIRED")
        before = {"operating_mode": machine.operating_mode, "status": machine.status}
        machine.operating_mode = mode
        machine.config_version += 1
        machine = self._with_live_status(machine)
        self.machines.update(machine)
        self.audit.record_user(ctx, "MACHINE_MODE_CHANGE", "machine", target_id=machine.id, before=before,
                               after={"operating_mode": mode}, severity="WARNING")
        self.uow.commit()
        return machine

    def revoke_device(self, ctx: AuthContext, machine_id: int) -> Machine:
        ctx.require_permission(P.MACHINE_MANAGE)
        machine = self._get_machine(ctx, machine_id)
        machine.revoked_at = self.clock()
        machine.status = MachineStatus.DISABLED.value
        machine.operating_mode = OperatingMode.DISABLED.value
        self.machines.update(machine)
        self.audit.record_user(ctx, "DEVICE_REVOKE", "machine", target_id=machine.id, severity="CRITICAL")
        self.uow.commit()
        return machine

    def configure_slot(self, ctx: AuthContext, slot_id: int, changes: dict) -> Slot:
        """changes may contain: product_id, price, dosage_ms, ml_per_spray, low_stock_threshold, enabled."""
        ctx.require_permission(P.SLOT_CONFIGURE)
        tenant_id = ctx.require_tenant()
        slot = self.slots.get(tenant_id, slot_id)
        if slot is None:
            raise NotFoundException("Slot not found")
        before = snapshot(slot, SLOT_WATCHED)

        if "product_id" in changes:
            product_id = changes["product_id"]
            product = None
            if product_id is not None:
                product = self.products.get(tenant_id, product_id)
                if product is None:
                    raise ValidationException("Unknown product")
            if slot.current_bottle_id and product_id != slot.product_id:
                raise BusinessRuleException("Remove the installed bottle before changing the perfume",
                                            "SLOT_HAS_BOTTLE")
            slot.product_id = product_id
            if product and "price" not in changes and Decimal(slot.price) == 0:
                slot.price = product.default_price_per_spray
        if "price" in changes:
            slot.price = to_decimal(changes["price"], "price", Decimal("0"))
        if "dosage_ms" in changes:
            if int(changes["dosage_ms"]) <= 0:
                raise ValidationException("dosage_ms must be > 0")
            slot.dosage_ms = int(changes["dosage_ms"])
        if "ml_per_spray" in changes:
            slot.ml_per_spray = to_decimal(changes["ml_per_spray"], "ml_per_spray", Decimal("0.001"))
        if "low_stock_threshold" in changes:
            if int(changes["low_stock_threshold"]) < 0:
                raise ValidationException("low_stock_threshold must be >= 0")
            slot.low_stock_threshold = int(changes["low_stock_threshold"])

        disabled = slot.status == SlotStatus.DISABLED.value
        if "enabled" in changes:
            disabled = not changes["enabled"]
        slot.status = slot_status_from_stock(slot.estimated_remaining_sprays, slot.low_stock_threshold, disabled)
        self.slots.update(slot)

        machine = self.machines.get_by_id(slot.machine_id)
        machine.config_version += 1
        self.machines.update(machine)

        after = snapshot(slot, SLOT_WATCHED)
        action = "SLOT_CONFIG"
        if before["price"] != after["price"]:
            action = "PRICE_CHANGE"
        elif before["product_id"] != after["product_id"]:
            action = "SLOT_ASSIGNMENT"
        self.audit.record_user(ctx, action, "slot", target_id=slot.id, before=before, after=after,
                               severity="WARNING" if action == "PRICE_CHANGE" else "INFO")
        self.uow.commit()
        return slot

    # ------------------------------------------------------------------ device side
    def authenticate_device(self, serial_number: str, secret: str) -> Machine:
        machine = self.machines.get_by_serial(serial_number or "")
        if machine is None or machine.revoked_at is not None or not self.devices.verify_secret(secret, machine.device_secret_hash):
            raise UnauthorizedException("Invalid device credentials")
        return machine

    def heartbeat(self, machine: Machine, payload: dict) -> dict:
        now = self.clock()
        machine.last_heartbeat_at = now
        if payload.get("firmware_version"):
            machine.firmware_version = payload["firmware_version"]
        machine = self._with_live_status(machine)
        self.machines.update(machine)
        self.alerts.resolve_by_key(AlertType.OFFLINE.value, machine.id)

        for item in payload.get("telemetry") or []:
            slot = self.slots.get_by_number(machine.id, item["slot_number"]) if item.get("slot_number") else None
            stored = self.device_data.add_telemetry_if_new(TelemetryRecord(
                tenant_id=machine.tenant_id, machine_id=machine.id, slot_id=slot.id if slot else None,
                event_uid=item["event_uid"], recorded_at=parse_datetime(item.get("recorded_at"), now), received_at=now,
                weight_g=item.get("weight_g"), estimated_remaining=item.get("estimated_remaining"),
                door_open=item.get("door_open"), leak_detected=item.get("leak_detected"),
                actuator_state=item.get("actuator_state"), power_status=item.get("power_status")))
            if not stored:
                continue                                   # already received (offline re-sync): no duplicate effects
            if item.get("door_open"):
                self.alerts.raise_alert(machine.tenant_id, machine.id, AlertType.DOOR_OPEN.value,
                                        Severity.WARNING.value, "Machine door is open")
            elif item.get("door_open") is False:
                self.alerts.resolve_by_key(AlertType.DOOR_OPEN.value, machine.id)
            if item.get("leak_detected"):
                self.alerts.raise_alert(machine.tenant_id, machine.id, AlertType.LEAKAGE.value,
                                        Severity.CRITICAL.value, "Possible leakage detected",
                                        slot_id=slot.id if slot else None)

        for item in payload.get("events") or []:
            event_type = item.get("event_type", DeviceEventType.OTHER.value)
            if event_type not in [e.value for e in DeviceEventType]:
                event_type = DeviceEventType.OTHER.value
            stored = self.device_data.add_event_if_new(DeviceEvent(
                tenant_id=machine.tenant_id, machine_id=machine.id, event_uid=item["event_uid"],
                event_type=event_type, error_code=item.get("error_code"), payload=item.get("payload"),
                recorded_at=parse_datetime(item.get("recorded_at"), now), received_at=now))
            if stored and event_type == DeviceEventType.SENSOR_ERROR.value:
                self.alerts.raise_alert(machine.tenant_id, machine.id, AlertType.SENSOR_FAILURE.value,
                                        Severity.WARNING.value, item.get("error_code") or "Sensor error")
        self.uow.commit()
        return {"server_time": now, "operating_mode": machine.operating_mode, "config_version": machine.config_version}

    # ------------------------------------------------------------------ background job
    def refresh_connectivity(self) -> int:
        """Mark machines OFFLINE when heartbeats stop and raise one alert per outage. Returns #changed."""
        now = self.clock()
        changed = 0
        for machine in self.machines.list(None):
            if machine.operating_mode != OperatingMode.NORMAL.value or machine.revoked_at is not None:
                continue
            status = connectivity(machine.last_heartbeat_at, now, self.settings)
            if status != machine.status:
                machine.status = status
                self.machines.update(machine)
                changed += 1
            if status == MachineStatus.OFFLINE.value:
                self.alerts.raise_alert(machine.tenant_id, machine.id, AlertType.OFFLINE.value,
                                        Severity.CRITICAL.value, "Machine stopped sending heartbeats")
        self.uow.commit()
        return changed

    # ------------------------------------------------------------------ helpers
    def _get_machine(self, ctx: AuthContext, machine_id: int) -> Machine:
        # platform users may read any machine, brand users only their own brand's machines
        machine = self.machines.get_by_id(machine_id) if ctx.tenant_id is None \
            else self.machines.get(ctx.tenant_id, machine_id)
        if machine is None:
            raise NotFoundException("Machine not found")
        return machine

    def _with_live_status(self, machine: Machine) -> Machine:
        if machine.operating_mode == OperatingMode.DISABLED.value:
            machine.status = MachineStatus.DISABLED.value
        elif machine.operating_mode == OperatingMode.MAINTENANCE.value:
            machine.status = MachineStatus.MAINTENANCE.value
        else:
            machine.status = connectivity(machine.last_heartbeat_at, self.clock(), self.settings)
        return machine
