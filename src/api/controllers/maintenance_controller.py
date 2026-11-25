from flask import Blueprint, g, request

from api.middleware import login_required
from api.requests import int_arg, validate_json
from api.responses import ok
from api.schemas.ops import (AssignTicketSchema, ChecklistItemSchema, CreateTicketSchema, PostTestSchema,
                             TicketResultSchema)
from dependency_container import container
from services.common import parse_datetime

maintenance_bp = Blueprint("maintenance", __name__, url_prefix="/api/v1/maintenance")


@maintenance_bp.route("/tickets", methods=["POST"])
@login_required
@validate_json(CreateTicketSchema)
def create_ticket():
    """Create a maintenance ticket (a CRITICAL open ticket blocks new orders on the machine)."""
    data = dict(g.json)
    data["due_at"] = parse_datetime(data.get("due_at"))
    return ok(container.maintenance_service().create_ticket(g.ctx, **data), 201)


@maintenance_bp.route("/tickets", methods=["GET"])
@login_required
def list_tickets():
    """List tickets: ?status=&machine_id=&limit=. A technician only sees the tickets assigned to them."""
    return ok(container.maintenance_service().list_tickets(
        g.ctx, request.args.get("status"), int_arg("machine_id"), int_arg("limit", 100)))


@maintenance_bp.route("/tickets/<int:ticket_id>", methods=["GET"])
@login_required
def get_ticket(ticket_id):
    """Ticket detail with its checklist."""
    return ok(container.maintenance_service().get_ticket(g.ctx, ticket_id))


@maintenance_bp.route("/tickets/<int:ticket_id>/assign", methods=["POST"])
@login_required
@validate_json(AssignTicketSchema)
def assign_ticket(ticket_id):
    """Assign the ticket to a technician of the same brand."""
    return ok(container.maintenance_service().assign(g.ctx, ticket_id, g.json["user_id"]))


@maintenance_bp.route("/tickets/<int:ticket_id>/start", methods=["POST"])
@login_required
def start_ticket(ticket_id):
    """Technician starts working on the ticket."""
    return ok(container.maintenance_service().start(g.ctx, ticket_id))


@maintenance_bp.route("/tickets/<int:ticket_id>/checklist/<int:item_id>", methods=["PUT"])
@login_required
@validate_json(ChecklistItemSchema)
def set_checklist_item(ticket_id, item_id):
    """Tick (or untick) one checklist item."""
    return ok(container.maintenance_service().set_checklist_item(g.ctx, ticket_id, item_id, **g.json))


@maintenance_bp.route("/tickets/<int:ticket_id>/result", methods=["PUT"])
@login_required
@validate_json(TicketResultSchema)
def record_result(ticket_id):
    """Record diagnosis, corrective action, replaced parts, cost and evidence."""
    return ok(container.maintenance_service().record_result(g.ctx, ticket_id, **g.json))


@maintenance_bp.route("/tickets/<int:ticket_id>/post-test", methods=["POST"])
@login_required
@validate_json(PostTestSchema)
def post_test(ticket_id):
    """Record the post-maintenance test result."""
    return ok(container.maintenance_service().record_post_test(g.ctx, ticket_id, g.json["passed"]))


@maintenance_bp.route("/tickets/<int:ticket_id>/close", methods=["POST"])
@login_required
def close_ticket(ticket_id):
    """Close the ticket: needs the repair result, a complete checklist and (for repairs) a passed post-test."""
    return ok(container.maintenance_service().close(g.ctx, ticket_id))
