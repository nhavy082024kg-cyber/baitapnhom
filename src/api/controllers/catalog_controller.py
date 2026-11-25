from flask import Blueprint, g, request

from api.middleware import login_required
from api.requests import validate_json
from api.responses import ok
from api.schemas.catalog import LocationSchema, ProductSchema
from api.schemas.ops import PromotionSchema
from dependency_container import container

product_bp = Blueprint("products", __name__, url_prefix="/api/v1/products")
location_bp = Blueprint("locations", __name__, url_prefix="/api/v1/locations")
promotion_bp = Blueprint("promotions", __name__, url_prefix="/api/v1/promotions")


@product_bp.route("", methods=["POST"])
@login_required
@validate_json(ProductSchema)
def create_product():
    """Create a perfume product in my brand."""
    return ok(container.product_service().create_product(g.ctx, g.json), 201)


@product_bp.route("", methods=["GET"])
@login_required
def list_products():
    """List the perfume products of my brand."""
    return ok(container.product_service().list_products(g.ctx))


@product_bp.route("/<int:product_id>", methods=["GET"])
@login_required
def get_product(product_id):
    """Get one product (404 if it belongs to another brand)."""
    return ok(container.product_service().get_product(g.ctx, product_id))


@product_bp.route("/<int:product_id>", methods=["PUT"])
@login_required
@validate_json(ProductSchema, partial=True)
def update_product(product_id):
    """Update a product. A price change is written to the audit log."""
    return ok(container.product_service().update_product(g.ctx, product_id, g.json))


@location_bp.route("", methods=["POST"])
@login_required
@validate_json(LocationSchema)
def create_location():
    """Create a location (shop, mall, event...)."""
    return ok(container.location_service().create_location(g.ctx, **g.json), 201)


@location_bp.route("", methods=["GET"])
@login_required
def list_locations():
    """List the locations of my brand."""
    return ok(container.location_service().list_locations(g.ctx))


@promotion_bp.route("", methods=["POST"])
@login_required
@validate_json(PromotionSchema)
def create_promotion():
    """Create a TEMP_PRICE promotion (DRAFT). Scope: a product, machine and/or location, or the whole brand."""
    return ok(container.promotion_service().create(g.ctx, **g.json), 201)


@promotion_bp.route("", methods=["GET"])
@login_required
def list_promotions():
    """List promotions: ?status=DRAFT|ACTIVE|ENDED."""
    return ok(container.promotion_service().list(g.ctx, request.args.get("status")))


@promotion_bp.route("/<int:promotion_id>/activate", methods=["POST"])
@login_required
def activate_promotion(promotion_id):
    """Activate a DRAFT promotion: it applies to new orders while now is between starts_at and ends_at."""
    return ok(container.promotion_service().activate(g.ctx, promotion_id))


@promotion_bp.route("/<int:promotion_id>/end", methods=["POST"])
@login_required
def end_promotion(promotion_id):
    """End a promotion now. Orders already created keep their price."""
    return ok(container.promotion_service().end(g.ctx, promotion_id))
