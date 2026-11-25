from decimal import Decimal
from typing import List, Optional

from domain.clock import utcnow
from domain.constants import P, PromotionStatus, PromotionType
from domain.exceptions import BusinessRuleException, NotFoundException, ValidationException
from domain.models.catalog import Product, Promotion
from domain.models.irepositories import (ILocationRepository, IMachineRepository, IProductRepository,
                                         IPromotionRepository, IUnitOfWork)
from domain.models.machine import Machine
from domain.models.user import AuthContext
from services.audit_service import AuditService
from services.common import parse_datetime, to_decimal


def pick_promotion_price(promotions: List[Promotion], product: Product, machine: Machine, base_price: Decimal):
    """Cheapest ACTIVE promotion that matches product / machine / location. Returns (price, promotion_id)."""
    best_price, best_id = Decimal(base_price), None
    for p in promotions:
        if p.temp_price is None:
            continue
        if p.product_id not in (None, product.id) or p.machine_id not in (None, machine.id):
            continue
        if p.location_id not in (None, machine.location_id):
            continue
        if Decimal(p.temp_price) < best_price:
            best_price, best_id = Decimal(p.temp_price), p.id
    return best_price, best_id


class PromotionService:
    """Temporary prices. The order keeps the price it was created with, so ending a promotion never changes old orders."""

    def __init__(self, promotions: IPromotionRepository, products: IProductRepository,
                 machines: IMachineRepository, locations: ILocationRepository, audit: AuditService,
                 uow: IUnitOfWork, clock=utcnow):
        self.promotions = promotions
        self.products = products
        self.machines = machines
        self.locations = locations
        self.audit = audit
        self.uow = uow
        self.clock = clock

    def create(self, ctx: AuthContext, name: str, type: str, starts_at, ends_at, temp_price=None,
               product_id: Optional[int] = None, machine_id: Optional[int] = None,
               location_id: Optional[int] = None) -> Promotion:
        ctx.require_permission(P.PRODUCT_MANAGE)
        tenant_id = ctx.require_tenant()
        if type == PromotionType.FREE_TRIAL.value:
            raise ValidationException("FREE_TRIAL is not supported yet: use TEMP_PRICE")
        if type != PromotionType.TEMP_PRICE.value:
            raise ValidationException("Invalid promotion type")
        starts, ends = parse_datetime(starts_at), parse_datetime(ends_at)
        if ends <= starts:
            raise ValidationException("ends_at must be after starts_at")
        price = to_decimal(temp_price, "temp_price", Decimal("1"))
        if product_id is not None and self.products.get(tenant_id, product_id) is None:
            raise ValidationException("Unknown product")
        if machine_id is not None and self.machines.get(tenant_id, machine_id) is None:
            raise ValidationException("Unknown machine")
        if location_id is not None and self.locations.get(tenant_id, location_id) is None:
            raise ValidationException("Unknown location")
        promotion = self.promotions.add(Promotion(
            tenant_id=tenant_id, name=name, type=type, temp_price=price, product_id=product_id,
            machine_id=machine_id, location_id=location_id, starts_at=starts, ends_at=ends,
            status=PromotionStatus.DRAFT.value))
        self.audit.record_user(ctx, "PROMOTION_CREATE", "promotion", target_id=promotion.id,
                               after={"name": name, "temp_price": price})
        self.uow.commit()
        return promotion

    def list(self, ctx: AuthContext, status: Optional[str] = None) -> List[Promotion]:
        ctx.require_permission(P.PRODUCT_VIEW)
        return self.promotions.list(ctx.require_tenant(), status)

    def activate(self, ctx: AuthContext, promotion_id: int) -> Promotion:
        promotion = self._get(ctx, promotion_id)
        if promotion.status != PromotionStatus.DRAFT.value:
            raise BusinessRuleException(f"Only a DRAFT promotion can be activated (is {promotion.status})",
                                        "PROMOTION_STATE")
        return self._set_status(ctx, promotion, PromotionStatus.ACTIVE.value, "PROMOTION_ACTIVATE")

    def end(self, ctx: AuthContext, promotion_id: int) -> Promotion:
        promotion = self._get(ctx, promotion_id)
        if promotion.status == PromotionStatus.ENDED.value:
            return promotion
        return self._set_status(ctx, promotion, PromotionStatus.ENDED.value, "PROMOTION_END")

    def _get(self, ctx: AuthContext, promotion_id: int) -> Promotion:
        ctx.require_permission(P.PRODUCT_MANAGE)
        promotion = self.promotions.get(ctx.require_tenant(), promotion_id)
        if promotion is None:
            raise NotFoundException("Promotion not found")
        return promotion

    def _set_status(self, ctx, promotion: Promotion, status: str, action: str) -> Promotion:
        before = {"status": promotion.status}
        promotion.status = status
        self.promotions.update(promotion)
        self.audit.record_user(ctx, action, "promotion", target_id=promotion.id, before=before,
                               after={"status": status})
        self.uow.commit()
        return promotion
