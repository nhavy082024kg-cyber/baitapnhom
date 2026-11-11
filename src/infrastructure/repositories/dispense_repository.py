from datetime import datetime
from typing import List

from domain.constants import CommandStatus, CommandType
from domain.models.device import DeviceEvent, TelemetryRecord
from domain.models.dispense import DispenseCommand
from domain.models.irepositories import IDeviceDataRepository, IDispenseCommandRepository
from infrastructure.models.dispense_models import DeviceEventModel, DeviceTelemetryModel, DispenseCommandModel
from infrastructure.repositories.base_repository import SqlRepository

OPEN = [CommandStatus.CREATED.value, CommandStatus.SENT.value, CommandStatus.ACKED.value]


class DispenseCommandRepository(SqlRepository, IDispenseCommandRepository):
    model, entity = DispenseCommandModel, DispenseCommand

    def add(self, command): return self._add(command)       # UNIQUE(order_id, type) is the last line of defence
    def get_by_command_id(self, command_id): return self._first(command_id=command_id)
    def get_sale_for_order(self, order_id): return self._first(order_id=order_id, type=CommandType.SALE.value)
    def list_for_order(self, order_id): return self._all(order_id=order_id)

    def list_open_for_machine(self, machine_id: int) -> List[DispenseCommand]:
        rows = self.session.query(DispenseCommandModel).filter(
            DispenseCommandModel.machine_id == machine_id,
            DispenseCommandModel.status.in_([CommandStatus.CREATED.value, CommandStatus.SENT.value])
        ).order_by(DispenseCommandModel.id).all()
        return self._to_entities(rows)

    def list_expired_open(self, now: datetime) -> List[DispenseCommand]:
        rows = self.session.query(DispenseCommandModel).filter(
            DispenseCommandModel.status.in_(OPEN), DispenseCommandModel.expires_at < now).all()
        return self._to_entities(rows)

    def update(self, command): return self._save(command)


class _TelemetryRepo(SqlRepository):
    model, entity = DeviceTelemetryModel, TelemetryRecord


class _EventRepo(SqlRepository):
    model, entity = DeviceEventModel, DeviceEvent


class DeviceDataRepository(IDeviceDataRepository):
    def __init__(self, session):
        self._telemetry, self._events = _TelemetryRepo(session), _EventRepo(session)

    def add_telemetry_if_new(self, record: TelemetryRecord) -> bool:
        return self._telemetry._add_if_new(record)       # UNIQUE(event_uid): offline re-sync is idempotent

    def add_event_if_new(self, event: DeviceEvent) -> bool:
        return self._events._add_if_new(event)
