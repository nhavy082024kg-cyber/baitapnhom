from flask import Blueprint, g, request

from api.middleware import login_required
from api.requests import validate_json
from api.responses import ok
from api.schemas.inventory import CreateBatchSchema, InstallBottleSchema, RegisterBottleSchema
from dependency_container import container

inventory_bp = Blueprint("inventory", __name__, url_prefix="/api/v1/inventory")


@inventory_bp.route("/batches", methods=["POST"])
@login_required
@validate_json(CreateBatchSchema)
def create_batch():
    """Register a batch of perfume bottles."""
    return ok(container.inventory_service().create_batch(g.ctx, **g.json), 201)


@inventory_bp.route("/batches", methods=["GET"])
@login_required
def list_batches():
    """List inventory batches."""
    return ok(container.inventory_service().list_batches(g.ctx))


@inventory_bp.route("/bottles", methods=["POST"])
@login_required
@validate_json(RegisterBottleSchema)
def register_bottle():
    """Register one bottle / cartridge with a unique code."""
    return ok(container.inventory_service().register_bottle(g.ctx, **g.json), 201)


@inventory_bp.route("/bottles", methods=["GET"])
@login_required
def list_bottles():
    """List bottles, optional filter ?status=AVAILABLE|INSTALLED|NEARLY_EMPTY|EMPTY|DAMAGED|EXPIRED."""
    return ok(container.inventory_service().list_bottles(g.ctx, request.args.get("status")))


@inventory_bp.route("/slots/<int:slot_id>/install-bottle", methods=["POST"])
@login_required
@validate_json(InstallBottleSchema)
def install_bottle(slot_id):
    """Install (or replace) the bottle of a slot. Rejects a wrong fragrance / expired bottle."""
    return ok(container.inventory_service().install_bottle(g.ctx, slot_id, **g.json))
