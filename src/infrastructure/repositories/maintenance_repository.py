from typing import List, Optional

from domain.models.irepositories import ITicketRepository
from domain.models.maintenance import ChecklistItem, MaintenanceTicket
from infrastructure.models.alert_models import MaintenanceChecklistItemModel, MaintenanceTicketModel
from infrastructure.repositories.base_repository import SqlRepository


class TicketRepository(SqlRepository, ITicketRepository):
    model, entity = MaintenanceTicketModel, MaintenanceTicket

    def add(self, ticket): return self._add(ticket)
    def get(self, tenant_id, ticket_id): return self._first(tenant_id=tenant_id, id=ticket_id)
    def find_by_alert(self, alert_id): return self._first(alert_id=alert_id)
    def update(self, ticket): return self._save(ticket)

    def list(self, tenant_id: int, status: Optional[str] = None, machine_id: Optional[int] = None,
             assigned_to: Optional[int] = None, limit: int = 100) -> List[MaintenanceTicket]:
        query = self.session.query(MaintenanceTicketModel).filter(MaintenanceTicketModel.tenant_id == tenant_id)
        if status:
            query = query.filter(MaintenanceTicketModel.status == status)
        if machine_id:
            query = query.filter(MaintenanceTicketModel.machine_id == machine_id)
        if assigned_to:
            query = query.filter(MaintenanceTicketModel.assigned_to == assigned_to)
        return self._to_entities(query.order_by(MaintenanceTicketModel.id.desc()).limit(limit).all())

    # checklist items live in another table: small dedicated helpers
    def add_item(self, item: ChecklistItem) -> ChecklistItem:
        data = {k: v for k, v in item.__dict__.items() if v is not None}
        row = MaintenanceChecklistItemModel(**data)
        self.session.add(row)
        self.session.flush()
        return self._item(row)

    def get_item(self, tenant_id, item_id):
        return self._item(self.session.query(MaintenanceChecklistItemModel)
                          .filter_by(tenant_id=tenant_id, id=item_id).first())

    def list_items(self, ticket_id):
        rows = (self.session.query(MaintenanceChecklistItemModel).filter_by(ticket_id=ticket_id)
                .order_by(MaintenanceChecklistItemModel.id).all())
        return [self._item(r) for r in rows]

    def update_item(self, item: ChecklistItem) -> ChecklistItem:
        row = self.session.query(MaintenanceChecklistItemModel).filter_by(id=item.id).one()
        for key in ("is_done", "note", "done_by", "done_at"):
            setattr(row, key, getattr(item, key))
        self.session.flush()
        return self._item(row)

    @staticmethod
    def _item(row) -> Optional[ChecklistItem]:
        if row is None:
            return None
        return ChecklistItem(**{k: getattr(row, k) for k in ChecklistItem.__dataclass_fields__})
