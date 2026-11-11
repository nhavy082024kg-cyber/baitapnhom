from flask import Blueprint, g

from api.middleware import login_required
from api.requests import validate_json
from api.responses import ok
from api.schemas.machine import ConfigureSlotSchema, ModeSchema, RegisterMachineSchema, TestSpraySchema
from dependency_container import container

machine_bp = Blueprint("machines", __name__, url_prefix="/api/v1/machines")
slot_bp = Blueprint("slots", __name__, url_prefix="/api/v1/slots")


@machine_bp.route("", methods=["POST"])
@login_required
@validate_json(RegisterMachineSchema)
def register_machine():
    """Register a kiosk and create its slots.

    The response contains `device_secret` ONCE: put it in the kiosk (header X-Device-Secret).
    """
    machine, secret = container.machine_service().register_machine(g.ctx, **g.json)
    return ok({"machine": machine, "device_secret": secret}, 201)


@machine_bp.route("", methods=["GET"])
@login_required
def list_machines():
    """List machines with live status (ONLINE / UNSTABLE / OFFLINE / MAINTENANCE / DISABLED)."""
    return ok(container.machine_service().list_machines(g.ctx))


@machine_bp.route("/<int:machine_id>", methods=["GET"])
@login_required
def get_machine(machine_id):
    """Machine details with its slots (perfume, price, remaining sprays)."""
    machine, slots = container.machine_service().get_machine(g.ctx, machine_id)
    return ok({"machine": machine, "slots": slots})


@machine_bp.route("/<int:machine_id>/mode", methods=["PATCH"])
@login_required
@validate_json(ModeSchema)
def set_mode(machine_id):
    """Enable (NORMAL), disable (DISABLED) or put in MAINTENANCE.

    Leaving MAINTENANCE requires post_test_passed=true.
    """
    return ok(container.machine_service().set_mode(g.ctx, machine_id, g.json["mode"], g.json["post_test_passed"]))


@machine_bp.route("/<int:machine_id>/revoke", methods=["POST"])
@login_required
def revoke_device(machine_id):
    """Revoke the device: it can no longer authenticate."""
    return ok(container.machine_service().revoke_device(g.ctx, machine_id))


@machine_bp.route("/<int:machine_id>/test-spray", methods=["POST"])
@login_required
@validate_json(TestSpraySchema)
def test_spray(machine_id):
    """Technician test spray (machine must be in MAINTENANCE, needs step-up). Recorded separately from sales."""
    return ok(container.dispensing_service().create_test_spray(g.ctx, machine_id, g.json["slot_number"]), 201)


@slot_bp.route("/<int:slot_id>", methods=["PUT"])
@login_required
@validate_json(ConfigureSlotSchema, partial=True)
def configure_slot(slot_id):
    """Configure a slot: perfume, price, dosage, low-stock threshold, enabled. Price changes are audited."""
    return ok(container.machine_service().configure_slot(g.ctx, slot_id, g.json))
