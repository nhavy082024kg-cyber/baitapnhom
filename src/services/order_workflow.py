from typing import Optional

from domain.clock import utcnow
from domain.constants import OrderStatus
from domain.models.irepositories import IOrderRepository
from domain.models.order import Order, OrderStatusHistory
from domain.models.order_state_machine import assert_transition


class OrderWorkflow:
    """The ONLY place that changes order.status: validates the transition and writes the history row."""

    def __init__(self, orders: IOrderRepository, clock=utcnow):
        self.orders = orders
        self.clock = clock

    def start(self, order: Order, actor_type: str, actor_id: Optional[int] = None) -> None:
        self.orders.add_history(OrderStatusHistory(
            tenant_id=order.tenant_id, order_id=order.id, from_status=None, to_status=order.status,
            actor_type=actor_type, actor_id=actor_id, created_at=self.clock()))

    def transition(self, order: Order, to_status: str, actor_type: str, actor_id: Optional[int] = None,
                   reason: Optional[str] = None) -> Order:
        assert_transition(order.status, to_status)
        previous = order.status
        order.status = to_status
        now = self.clock()
        if to_status == OrderStatus.PAID.value:
            order.paid_at = now
        elif to_status == OrderStatus.DISPENSED.value:
            order.dispensed_at = now
        self.orders.update(order)
        self.orders.add_history(OrderStatusHistory(
            tenant_id=order.tenant_id, order_id=order.id, from_status=previous, to_status=to_status,
            reason=reason, actor_type=actor_type, actor_id=actor_id, created_at=now))
        return order
