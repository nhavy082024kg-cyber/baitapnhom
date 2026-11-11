from datetime import datetime
from typing import List, Optional

from domain.constants import OrderStatus
from domain.models.irepositories import (IOrderRepository, IPaymentRepository, IRefundRepository,
                                         IWebhookEventRepository)
from domain.models.order import Order, OrderStatusHistory, Payment, Refund, WebhookEvent
from infrastructure.models.order_models import (OrderModel, OrderStatusHistoryModel, PaymentModel,
                                                PaymentWebhookEventModel, RefundModel)
from infrastructure.repositories.base_repository import SqlRepository


class OrderRepository(SqlRepository, IOrderRepository):
    model, entity = OrderModel, Order

    def add(self, order): return self._add(order)
    def get(self, tenant_id, order_id): return self._first(tenant_id=tenant_id, id=order_id)
    def get_by_id(self, order_id): return self._first(id=order_id)
    def get_by_code(self, order_code): return self._first(order_code=order_code)

    def list(self, tenant_id: int, status: Optional[str] = None, machine_id: Optional[int] = None,
             limit: int = 100) -> List[Order]:
        query = self.session.query(OrderModel).filter(OrderModel.tenant_id == tenant_id)
        if status:
            query = query.filter(OrderModel.status == status)
        if machine_id:
            query = query.filter(OrderModel.machine_id == machine_id)
        return self._to_entities(query.order_by(OrderModel.id.desc()).limit(limit).all())

    def update(self, order): return self._save(order)

    def add_history(self, history: OrderStatusHistory) -> OrderStatusHistory:
        data = {k: v for k, v in history.__dict__.items() if v is not None}
        row = OrderStatusHistoryModel(**data)
        self.session.add(row)
        self.session.flush()
        return OrderStatusHistory(**{k: getattr(row, k) for k in history.__dict__})

    def list_history(self, order_id: int) -> List[OrderStatusHistory]:
        rows = (self.session.query(OrderStatusHistoryModel).filter_by(order_id=order_id)
                .order_by(OrderStatusHistoryModel.id).all())
        return [OrderStatusHistory(**{k: getattr(r, k) for k in OrderStatusHistory.__dataclass_fields__}) for r in rows]

    def list_overdue_awaiting_payment(self, now: datetime) -> List[Order]:
        rows = self.session.query(OrderModel).filter(OrderModel.status == OrderStatus.AWAITING_PAYMENT.value,
                                                     OrderModel.expires_at <= now).all()
        return self._to_entities(rows)


class PaymentRepository(SqlRepository, IPaymentRepository):
    model, entity = PaymentModel, Payment

    def add(self, payment): return self._add(payment)
    def get_by_reference(self, payment_reference): return self._first(payment_reference=payment_reference)
    def get_by_order(self, order_id): return self._first(order_id=order_id)
    def update(self, payment): return self._save(payment)


class WebhookEventRepository(SqlRepository, IWebhookEventRepository):
    model, entity = PaymentWebhookEventModel, WebhookEvent

    def add_if_new(self, event: WebhookEvent) -> bool:
        if self._first(provider_event_id=event.provider_event_id) is not None:
            return False
        return self._add_if_new(event)           # also safe against two simultaneous deliveries (UNIQUE)

    def mark_processed(self, provider_event_id: str, payment_id: Optional[int] = None) -> None:
        row = self.session.query(PaymentWebhookEventModel).filter_by(provider_event_id=provider_event_id).one()
        row.processed = True
        if payment_id is not None:
            row.payment_id = payment_id
        self.session.flush()


class RefundRepository(SqlRepository, IRefundRepository):
    model, entity = RefundModel, Refund

    def add(self, refund): return self._add(refund)
    def list_by_order(self, order_id): return self._all(order_id=order_id)
