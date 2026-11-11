from flask import Blueprint, g

from api.middleware import login_required
from api.requests import validate_json
from api.responses import ok
from api.schemas.catalog import LocationSchema, ProductSchema
from dependency_container import container

product_bp = Blueprint("products", __name__, url_prefix="/api/v1/products")
location_bp = Blueprint("locations", __name__, url_prefix="/api/v1/locations")


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
