from typing import List, Optional

from domain.models.inventory import Bottle, InventoryBatch, InventoryLog
from domain.models.irepositories import IInventoryRepository
from infrastructure.models.inventory_models import BottleModel, InventoryBatchModel, InventoryLogModel
from infrastructure.repositories.base_repository import SqlRepository


class InventoryRepository(SqlRepository, IInventoryRepository):
    """One repository for batches + bottles + logs (they are always used together)."""
    model, entity = BottleModel, Bottle

    @staticmethod
    def _map(row, entity_cls):
        from dataclasses import fields
        return None if row is None else entity_cls(**{f.name: getattr(row, f.name) for f in fields(entity_cls)})

    def add_batch(self, batch: InventoryBatch) -> InventoryBatch:
        row = InventoryBatchModel(**{k: v for k, v in batch.__dict__.items() if v is not None})
        self.session.add(row)
        self.session.flush()
        return self._map(row, InventoryBatch)

    def get_batch(self, tenant_id, batch_id):
        return self._map(self.session.query(InventoryBatchModel).filter_by(tenant_id=tenant_id, id=batch_id).first(),
                         InventoryBatch)

    def list_batches(self, tenant_id) -> List[InventoryBatch]:
        rows = self.session.query(InventoryBatchModel).filter_by(tenant_id=tenant_id).order_by(InventoryBatchModel.id)
        return [self._map(r, InventoryBatch) for r in rows]

    def add_bottle(self, bottle): return self._add(bottle)
    def get_bottle(self, tenant_id, bottle_id): return self._first(tenant_id=tenant_id, id=bottle_id)
    def get_bottle_by_code(self, tenant_id, unique_code): return self._first(tenant_id=tenant_id, unique_code=unique_code)

    def list_bottles(self, tenant_id: int, status: Optional[str] = None) -> List[Bottle]:
        query = self.session.query(BottleModel).filter_by(tenant_id=tenant_id)
        if status:
            query = query.filter_by(status=status)
        return self._to_entities(query.order_by(BottleModel.id).all())

    def update_bottle(self, bottle): return self._save(bottle)

    def add_log(self, log: InventoryLog) -> InventoryLog:
        row = InventoryLogModel(**{k: v for k, v in log.__dict__.items() if v is not None})
        self.session.add(row)
        self.session.flush()
        return self._map(row, InventoryLog)
