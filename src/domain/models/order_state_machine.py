# Order state machine. Every status change MUST go through assert_transition().
#
#  CREATED -> AWAITING_PAYMENT -> PAID -> DISPENSING -> DISPENSED
#                 |                |          |
#                 |                |          +-> DISPENSE_FAILED / UNCERTAIN -> MANUAL_REVIEW -> REFUNDED
#                 |                +-> MANUAL_REVIEW (paid but machine can no longer dispense)
#                 +-> EXPIRED / CANCELLED (a late payment moves them to MANUAL_REVIEW)

from domain.constants import OrderStatus as S
from domain.exceptions import InvalidStateTransition

ALLOWED_TRANSITIONS = {
    S.CREATED.value: {S.AWAITING_PAYMENT.value, S.CANCELLED.value},
    S.AWAITING_PAYMENT.value: {S.PAID.value, S.EXPIRED.value, S.CANCELLED.value},
    S.PAID.value: {S.DISPENSING.value, S.MANUAL_REVIEW.value},
    S.DISPENSING.value: {S.DISPENSED.value, S.DISPENSE_FAILED.value, S.UNCERTAIN.value},
    S.DISPENSE_FAILED.value: {S.MANUAL_REVIEW.value, S.REFUNDED.value},
    S.UNCERTAIN.value: {S.MANUAL_REVIEW.value, S.REFUNDED.value},
    S.MANUAL_REVIEW.value: {S.REFUNDED.value, S.DISPENSED.value},
    S.EXPIRED.value: {S.MANUAL_REVIEW.value},
    S.CANCELLED.value: {S.MANUAL_REVIEW.value},
    S.DISPENSED.value: set(),
    S.REFUNDED.value: set(),
}


def can_transition(current: str, target: str) -> bool:
    return target in ALLOWED_TRANSITIONS.get(current, set())


def assert_transition(current: str, target: str) -> None:
    if not can_transition(current, target):
        raise InvalidStateTransition(f"Order cannot go from {current} to {target}")
