import uuid
from datetime import timedelta
from typing import List, Optional

from domain.clock import utcnow
from domain.constants import (ActorType, AlertType, CommandStatus, CommandType, OperatingMode, OrderStatus,
                              P, Severity)
from domain.exceptions import BusinessRuleException, NotFoundException, ValidationException
from domain.models.dispense import DispenseCommand
from domain.models.dispense_policy import machine_block_reason, slot_block_reason
from domain.models.irepositories import (IDispenseCommandRepository, IMachineRepository, IOrderRepository,
                                         ISlotRepository, IUnitOfWork)
from domain.models.iservices import IDeviceSecurity
from domain.models.machine import Machine
from domain.models.order import Order
from domain.models.settings import ServiceSettings
from domain.models.user import AuthContext
from services.alert_service import AlertService
from services.audit_service import AuditService
from services.inventory_service import InventoryService
from services.order_workflow import OrderWorkflow

DEVICE_RESULTS = {CommandStatus.EXECUTED.value, CommandStatus.FAILED.value, CommandStatus.REJECTED.value}
OPEN_STATUSES = {CommandStatus.CREATED.value, CommandStatus.SENT.value, CommandStatus.ACKED.value}


class DispensingService:
    """
    Guarantee: one paid order -> at most ONE spray.
      * create_sale_command() is idempotent and the DB has UNIQUE(order_id, type)
      * the device must ACK, then execute, then report a result
      * timeout / failure NEVER creates a second command: the order goes to MANUAL_REVIEW
    """

    def __init__(self, commands: IDispenseCommandRepository, orders: IOrderRepository, slots: ISlotRepository,
                 machines: IMachineRepository, devices: IDeviceSecurity, inventory: InventoryService,
                 alerts: AlertService, workflow: OrderWorkflow, audit: AuditService, uow: IUnitOfWork,
                 settings: ServiceSettings, clock=utcnow):
        self.commands = commands
        self.orders = orders
        self.slots = slots
        self.machines = machines
        self.devices = devices
        self.inventory = inventory
        self.alerts = alerts
        self.workflow = workflow
        self.audit = audit
        self.uow = uow
        self.settings = settings
        self.clock = clock

    # ------------------------------------------------------------------ backend -> device
    def create_sale_command(self, order: Order) -> Optional[DispenseCommand]:
        """Called by PaymentService right after the backend verified the payment. No commit here."""
        existing = self.commands.get_sale_for_order(order.id)
        if existing:
            return existing                                    # idempotent: never a second command
        now = self.clock()
        machine = self.machines.get_by_id(order.machine_id)
        slot = self.slots.get_by_id(order.slot_id)
        reason = machine_block_reason(machine, now, self.settings) or slot_block_reason(slot)
        if reason:                                             # paid, but we cannot spray: humans decide (refund)
            self.workflow.transition(order, OrderStatus.MANUAL_REVIEW.value, ActorType.SYSTEM.value,
                                     reason=f"Cannot dispense: {reason}")
            self.audit.record(action="DISPENSE_BLOCKED", target_type="order", target_id=order.id,
                              order_id=order.id, tenant_id=order.tenant_id, actor_type=ActorType.SYSTEM.value,
                              after={"reason": reason}, severity="WARNING")
            return None
        command = self._new_command(machine, slot, CommandType.SALE.value, order_id=order.id)
        self.workflow.transition(order, OrderStatus.DISPENSING.value, ActorType.SYSTEM.value,
                                 reason=f"Command {command.command_id}")
        self.audit.record(action="DISPENSE_COMMAND_CREATE", target_type="dispense_command", target_id=command.id,
                          order_id=order.id, tenant_id=order.tenant_id, actor_type=ActorType.SYSTEM.value,
                          after={"command_id": command.command_id})
        return command

    def create_test_spray(self, ctx: AuthContext, machine_id: int, slot_number: int) -> DispenseCommand:
        """Technician diagnostic spray: recorded separately from customer sales."""
        ctx.require_permission(P.DEVICE_TEST_SPRAY)
        tenant_id = ctx.require_tenant()
        ctx.require_step_up(self.clock())
        machine = self.machines.get(tenant_id, machine_id)
        if machine is None:
            raise NotFoundException("Machine not found")
        if machine.operating_mode != OperatingMode.MAINTENANCE.value:
            raise BusinessRuleException("Put the machine in maintenance mode before a test spray", "NOT_IN_MAINTENANCE")
        slot = self.slots.get_by_number(machine.id, slot_number)
        if slot is None:
            raise NotFoundException("Slot not found")
        if slot.product_id is None or slot.estimated_remaining_sprays < 1:
            raise BusinessRuleException("Slot is empty", "SLOT_UNAVAILABLE")
        command = self._new_command(machine, slot, CommandType.TEST.value, requested_by=ctx.user_id)
        self.audit.record_user(ctx, "TEST_SPRAY_REQUEST", "dispense_command", target_id=command.id,
                               after={"command_id": command.command_id, "slot": slot_number})
        self.uow.commit()
        return command

    # ------------------------------------------------------------------ device -> backend
    def poll_commands(self, machine: Machine) -> List[dict]:
        now = self.clock()
        result = []
        for command in self.commands.list_open_for_machine(machine.id):
            if command.expires_at <= now:
                continue                                       # expire_stale_commands() will handle it
            slot = self.slots.get_by_id(command.slot_id)
            if command.status == CommandStatus.CREATED.value:
                command.status = CommandStatus.SENT.value
                self.commands.update(command)
            result.append({
                "command_id": command.command_id, "type": command.type, "machine_serial": machine.serial_number,
                "slot_number": slot.slot_number, "dosage_ms": slot.dosage_ms,
                "expires_at": command.expires_at, "signature": command.signature,
            })
        self.uow.commit()
        return result

    def acknowledge(self, machine: Machine, command_id: str) -> DispenseCommand:
        command = self._get_machine_command(machine, command_id)
        if command.status in (CommandStatus.CREATED.value, CommandStatus.SENT.value):
            command.status = CommandStatus.ACKED.value
            command.ack_at = self.clock()
            self.commands.update(command)
            self.uow.commit()
        return command                                         # repeated ACK is harmless

    def report_result(self, machine: Machine, command_id: str, status: str,
                      failure_code: Optional[str] = None, sensor_data: Optional[dict] = None) -> DispenseCommand:
        if status not in DEVICE_RESULTS:
            raise ValidationException(f"status must be one of {sorted(DEVICE_RESULTS)}")
        command = self._get_machine_command(machine, command_id)
        now = self.clock()

        if command.status in DEVICE_RESULTS:
            return command                                     # duplicate report: idempotent, nothing changes

        slot = self.slots.get_by_id(command.slot_id)
        order = self.orders.get_by_id(command.order_id) if command.order_id else None

        if command.status == CommandStatus.TIMEOUT.value:
            # Result arrived after we already declared the order uncertain: keep the order in review,
            # but record the truth so the Operations Manager can decide (refund or confirm).
            command.sensor_data = {**(sensor_data or {}), "late_result": status}
            command.failure_code = failure_code
            if status == CommandStatus.EXECUTED.value:
                command.executed_at = now
                self.inventory.deduct_spray(slot, order_id=command.order_id,
                                            test=command.type == CommandType.TEST.value,
                                            performed_by=command.requested_by)
            self.commands.update(command)
            self.audit.record(action="LATE_DEVICE_RESULT", target_type="dispense_command", target_id=command.id,
                              order_id=command.order_id, tenant_id=machine.tenant_id,
                              actor_type=ActorType.DEVICE.value, actor_id=machine.id,
                              after={"status": status, "failure_code": failure_code}, severity="WARNING")
            self.uow.commit()
            return command

        command.status = status
        command.failure_code = failure_code
        command.sensor_data = sensor_data
        if status == CommandStatus.EXECUTED.value:
            command.executed_at = now
        self.commands.update(command)

        if command.type == CommandType.TEST.value:
            if status == CommandStatus.EXECUTED.value:
                self.inventory.deduct_spray(slot, test=True, performed_by=command.requested_by)
        elif order is not None and order.status == OrderStatus.DISPENSING.value:
            if status == CommandStatus.EXECUTED.value:
                self.workflow.transition(order, OrderStatus.DISPENSED.value, ActorType.DEVICE.value, machine.id)
                self.inventory.deduct_spray(slot, order_id=order.id)
            else:
                self._send_to_review(order, OrderStatus.DISPENSE_FAILED.value,
                                     f"Device reported {status}: {failure_code or 'no code'}", machine.id)
                self.alerts.raise_alert(order.tenant_id, machine.id, AlertType.DISPENSE_FAILURE.value,
                                        Severity.WARNING.value, f"Dispense failed: {failure_code or status}",
                                        slot_id=slot.id)
        self.audit.record(action="DISPENSE_RESULT", target_type="dispense_command", target_id=command.id,
                          order_id=command.order_id, tenant_id=machine.tenant_id,
                          actor_type=ActorType.DEVICE.value, actor_id=machine.id,
                          after={"status": status, "failure_code": failure_code})
        self.uow.commit()
        return command

    # ------------------------------------------------------------------ background job
    def expire_stale_commands(self) -> int:
        """
        Commands the device never finished.
          never ACKed  -> we know nothing was sprayed  -> DISPENSE_FAILED -> MANUAL_REVIEW
          ACKed only   -> the device may have sprayed  -> UNCERTAIN       -> MANUAL_REVIEW
        In both cases NO new command is created.
        """
        count = 0
        for command in self.commands.list_expired_open(self.clock()):
            was_acked = command.status == CommandStatus.ACKED.value
            command.status = CommandStatus.TIMEOUT.value
            self.commands.update(command)
            count += 1
            order = self.orders.get_by_id(command.order_id) if command.order_id else None
            if order is not None and order.status == OrderStatus.DISPENSING.value:
                self._send_to_review(order, OrderStatus.UNCERTAIN.value if was_acked else OrderStatus.DISPENSE_FAILED.value,
                                     "Device did not confirm the spray in time", None)
                self.alerts.raise_alert(order.tenant_id, command.machine_id, AlertType.DISPENSE_FAILURE.value,
                                        Severity.WARNING.value, "Dispense command timed out", slot_id=command.slot_id)
        self.uow.commit()
        return count

    # ------------------------------------------------------------------ helpers
    def _new_command(self, machine: Machine, slot, command_type: str, order_id: Optional[int] = None,
                     requested_by: Optional[int] = None) -> DispenseCommand:
        now = self.clock()
        command_id = str(uuid.uuid4())
        # MySQL DATETIME has no microseconds: truncate NOW, otherwise the signed value != the stored value
        expires_at = (now + timedelta(seconds=self.settings.command_ttl_seconds)).replace(microsecond=0)
        signature = self.devices.sign_command(
            self.devices.derive_secret(machine.serial_number), command_id, machine.serial_number,
            slot.slot_number, command_type, expires_at.isoformat())
        return self.commands.add(DispenseCommand(
            tenant_id=machine.tenant_id, command_id=command_id, order_id=order_id, machine_id=machine.id,
            slot_id=slot.id, type=command_type, status=CommandStatus.CREATED.value, signature=signature,
            expires_at=expires_at, requested_by=requested_by, created_at=now))

    def _send_to_review(self, order: Order, failure_status: str, reason: str, machine_id: Optional[int]) -> None:
        actor = ActorType.DEVICE.value if machine_id else ActorType.SYSTEM.value
        self.workflow.transition(order, failure_status, actor, machine_id, reason)
        self.workflow.transition(order, OrderStatus.MANUAL_REVIEW.value, ActorType.SYSTEM.value,
                                 reason="Awaiting operations review (refund or manual confirmation)")

    def _get_machine_command(self, machine: Machine, command_id: str) -> DispenseCommand:
        command = self.commands.get_by_command_id(command_id)
        if command is None or command.machine_id != machine.id:    # a machine can only touch its own commands
            raise NotFoundException("Command not found")
        return command
