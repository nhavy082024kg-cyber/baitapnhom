from typing import List, Optional

from domain.constants import TicketSeverity, TicketStatus
from domain.models.irepositories import IMachineRepository, ISlotRepository
from domain.models.machine import Machine, Slot
from infrastructure.models.alert_models import MaintenanceTicketModel
from infrastructure.models.machine_models import MachineModel, SlotModel
from infrastructure.repositories.base_repository import SqlRepository


class MachineRepository(SqlRepository, IMachineRepository):
    model, entity = MachineModel, Machine

    def add(self, machine): return self._add(machine)
    def get(self, tenant_id, machine_id): return self._first(tenant_id=tenant_id, id=machine_id)
    def get_by_id(self, machine_id): return self._first(id=machine_id)
    def get_by_serial(self, serial_number): return self._first(serial_number=serial_number)

    def list(self, tenant_id: Optional[int]) -> List[Machine]:
        query = self.session.query(MachineModel)
        if tenant_id is not None:
            query = query.filter(MachineModel.tenant_id == tenant_id)
        return self._to_entities(query.order_by(MachineModel.id).all())

    def update(self, machine): return self._save(machine)

    def has_critical_open_ticket(self, machine_id: int) -> bool:
        return self.session.query(MaintenanceTicketModel.id).filter(
            MaintenanceTicketModel.machine_id == machine_id,
            MaintenanceTicketModel.severity == TicketSeverity.CRITICAL.value,
            MaintenanceTicketModel.status != TicketStatus.CLOSED.value).first() is not None


class SlotRepository(SqlRepository, ISlotRepository):
    model, entity = SlotModel, Slot

    def add(self, slot): return self._add(slot)
    def get(self, tenant_id, slot_id): return self._first(tenant_id=tenant_id, id=slot_id)
    def get_by_id(self, slot_id): return self._first(id=slot_id)
    def get_by_number(self, machine_id, slot_number): return self._first(machine_id=machine_id, slot_number=slot_number)

    def list_by_machine(self, machine_id: int) -> List[Slot]:
        return self._to_entities(self.session.query(SlotModel).filter_by(machine_id=machine_id)
                                 .order_by(SlotModel.slot_number).all())

    def update(self, slot): return self._save(slot)
