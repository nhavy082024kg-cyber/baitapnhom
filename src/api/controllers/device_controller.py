from flask import Blueprint, g

from api.middleware import device_required
from api.requests import validate_json
from api.responses import ok
from api.schemas.machine import CommandResultSchema, HeartbeatSchema
from dependency_container import container

device_bp = Blueprint("device", __name__, url_prefix="/api/v1/device")


@device_bp.route("/heartbeat", methods=["POST"])
@device_required
@validate_json(HeartbeatSchema)
def heartbeat():
    """Heartbeat + telemetry + events (event_uid makes re-sent data idempotent). Returns mode and config_version."""
    return ok(container.machine_service().heartbeat(g.device, g.json))


@device_bp.route("/commands", methods=["GET"])
@device_required
def poll_commands():
    """Pull pending signed commands (SALE / TEST). The device verifies signature + expiry before acting."""
    return ok(container.dispensing_service().poll_commands(g.device))


@device_bp.route("/commands/<command_id>/ack", methods=["POST"])
@device_required
def acknowledge(command_id):
    """Acknowledge a command BEFORE executing it."""
    return ok(container.dispensing_service().acknowledge(g.device, command_id))


@device_bp.route("/commands/<command_id>/result", methods=["POST"])
@device_required
@validate_json(CommandResultSchema)
def result(command_id):
    """Report EXECUTED / FAILED / REJECTED. The order becomes DISPENSED only after EXECUTED."""
    return ok(container.dispensing_service().report_result(
        g.device, command_id, g.json["status"], g.json.get("failure_code"), g.json.get("sensor_data")))
