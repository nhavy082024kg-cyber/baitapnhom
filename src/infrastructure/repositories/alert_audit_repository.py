from typing import List, Optional

from domain.constants import AlertStatus
from domain.models.device import Alert, AuditLog
from domain.models.irepositories import IAlertRepository, IAuditRepository
from infrastructure.models.alert_models import AlertModel
from infrastructure.models.audit_models import AuditLogModel
from infrastructure.repositories.base_repository import SqlRepository


class AlertRepository(SqlRepository, IAlertRepository):
    model, entity = AlertModel, Alert

    def add(self, alert): return self._add(alert)
    def get(self, tenant_id, alert_id): return self._first(tenant_id=tenant_id, id=alert_id)

    def find_open_by_dedup(self, dedup_key: str) -> Optional[Alert]:
        row = self.session.query(AlertModel).filter(AlertModel.dedup_key == dedup_key,
                                                    AlertModel.status != AlertStatus.RESOLVED.value).first()
        return self._to_entity(row)

    def list(self, tenant_id: Optional[int], status: Optional[str] = None, limit: int = 100) -> List[Alert]:
        query = self.session.query(AlertModel)
        if tenant_id is not None:
            query = query.filter(AlertModel.tenant_id == tenant_id)
        if status:
            query = query.filter(AlertModel.status == status)
        return self._to_entities(query.order_by(AlertModel.id.desc()).limit(limit).all())

    def update(self, alert): return self._save(alert)


class AuditRepository(SqlRepository, IAuditRepository):
    """Append-only: add() and search() only. There is deliberately no update/delete."""
    model, entity = AuditLogModel, AuditLog

    def add(self, log): return self._add(log)

    def search(self, tenant_id: Optional[int], action: Optional[str] = None, order_id: Optional[int] = None,
               limit: int = 100) -> List[AuditLog]:
        query = self.session.query(AuditLogModel)
        if tenant_id is not None:
            query = query.filter(AuditLogModel.tenant_id == tenant_id)
        if action:
            query = query.filter(AuditLogModel.action == action)
        if order_id:
            query = query.filter(AuditLogModel.order_id == order_id)
        return self._to_entities(query.order_by(AuditLogModel.id.desc()).limit(limit).all())
