from typing import List

from domain.constants import P
from domain.exceptions import ConflictException, NotFoundException, ValidationException
from domain.models.base import snapshot
from domain.models.catalog import Location, Product
from domain.models.irepositories import ILocationRepository, IProductRepository, IUnitOfWork
from domain.models.user import AuthContext
from services.audit_service import AuditService
from services.common import to_decimal

PRODUCT_EDITABLE = ["name", "description", "image_url", "top_notes", "middle_notes", "base_notes",
                    "usage_instructions", "product_qr_url", "is_available"]


class ProductService:
    def __init__(self, products: IProductRepository, audit: AuditService, uow: IUnitOfWork):
        self.products = products
        self.audit = audit
        self.uow = uow

    def create_product(self, ctx: AuthContext, data: dict) -> Product:
        ctx.require_permission(P.PRODUCT_MANAGE)
        tenant_id = ctx.require_tenant()
        sku = data["sku"].strip().upper()
        if any(p.sku == sku for p in self.products.list(tenant_id)):
            raise ConflictException("SKU already exists in this brand")
        price = to_decimal(data["default_price_per_spray"], "default_price_per_spray")
        if price <= 0:
            raise ValidationException("default_price_per_spray must be > 0")
        product = Product(tenant_id=tenant_id, sku=sku, name=data["name"].strip(), default_price_per_spray=price,
                          **{k: data.get(k) for k in PRODUCT_EDITABLE if k != "is_available" and k != "name"},
                          )
        product.is_available = data.get("is_available", True)
        product = self.products.add(product)
        self.audit.record_user(ctx, "PRODUCT_CREATE", "product", target_id=product.id,
                               after=snapshot(product, ["sku", "name", "default_price_per_spray"]))
        self.uow.commit()
        return product

    def list_products(self, ctx: AuthContext) -> List[Product]:
        ctx.require_permission(P.PRODUCT_VIEW)
        return self.products.list(ctx.require_tenant())

    def get_product(self, ctx: AuthContext, product_id: int) -> Product:
        ctx.require_permission(P.PRODUCT_VIEW)
        product = self.products.get(ctx.require_tenant(), product_id)
        if product is None:
            raise NotFoundException("Product not found")
        return product

    def update_product(self, ctx: AuthContext, product_id: int, data: dict) -> Product:
        ctx.require_permission(P.PRODUCT_MANAGE)
        product = self.products.get(ctx.require_tenant(), product_id)
        if product is None:
            raise NotFoundException("Product not found")
        before = snapshot(product, PRODUCT_EDITABLE + ["default_price_per_spray"])
        for key in PRODUCT_EDITABLE:
            if key in data:
                setattr(product, key, data[key])
        if "default_price_per_spray" in data:
            price = to_decimal(data["default_price_per_spray"], "default_price_per_spray")
            if price <= 0:
                raise ValidationException("default_price_per_spray must be > 0")
            product.default_price_per_spray = price
        self.products.update(product)
        after = snapshot(product, PRODUCT_EDITABLE + ["default_price_per_spray"])
        price_changed = before["default_price_per_spray"] != after["default_price_per_spray"]
        self.audit.record_user(ctx, "PRICE_CHANGE" if price_changed else "PRODUCT_UPDATE", "product",
                               target_id=product.id, before=before, after=after,
                               severity="WARNING" if price_changed else "INFO")
        self.uow.commit()
        return product


class LocationService:
    def __init__(self, locations: ILocationRepository, audit: AuditService, uow: IUnitOfWork):
        self.locations = locations
        self.audit = audit
        self.uow = uow

    def create_location(self, ctx: AuthContext, name: str, address=None, city=None) -> Location:
        ctx.require_permission(P.LOCATION_MANAGE)
        location = self.locations.add(Location(tenant_id=ctx.require_tenant(), name=name.strip(),
                                               address=address, city=city))
        self.audit.record_user(ctx, "LOCATION_CREATE", "location", target_id=location.id,
                               after=snapshot(location, ["name", "address", "city"]))
        self.uow.commit()
        return location

    def list_locations(self, ctx: AuthContext) -> List[Location]:
        ctx.require_permission(P.MACHINE_VIEW)
        return self.locations.list(ctx.require_tenant())
