
from marshmallow import Schema, fields, validate


class CreateTicketSchema(Schema):
    machine_id = fields.Int(required=True)
    category = fields.Str(required=True, validate=validate.OneOf(["INSPECTION", "REPAIR", "REFILL_SUPPORT", "POST_MAINTENANCE"]))
    severity = fields.Str(required=True, validate=validate.OneOf(["LOW", "MEDIUM", "HIGH", "CRITICAL"]))
    title = fields.Str(required=True, validate=validate.Length(min=3, max=200))
    description = fields.Str(allow_none=True)
    priority = fields.Str(load_default="NORMAL", validate=validate.OneOf(["LOW", "NORMAL", "HIGH", "URGENT"]))
    alert_id = fields.Int(allow_none=True)
    due_at = fields.Str(allow_none=True)


class AssignTicketSchema(Schema):
    user_id = fields.Int(required=True)


class ChecklistItemSchema(Schema):
    done = fields.Bool(load_default=True)
    note = fields.Str(allow_none=True, validate=validate.Length(max=500))


class TicketResultSchema(Schema):
    diagnosis = fields.Str(required=True, validate=validate.Length(min=3))
    corrective_action = fields.Str(required=True, validate=validate.Length(min=3))
    replaced_parts = fields.List(fields.Str(), load_default=list)
    cost = fields.Decimal(allow_none=True)
    evidence_urls = fields.List(fields.Str(), load_default=list)


class PostTestSchema(Schema):
    passed = fields.Bool(required=True)


class PromotionSchema(Schema):
    name = fields.Str(required=True, validate=validate.Length(min=2, max=150))
    type = fields.Str(load_default="TEMP_PRICE", validate=validate.OneOf(["TEMP_PRICE", "FREE_TRIAL"]))
    temp_price = fields.Decimal(allow_none=True)
    starts_at = fields.Str(required=True)
    ends_at = fields.Str(required=True)
    product_id = fields.Int(allow_none=True)
    machine_id = fields.Int(allow_none=True)
    location_id = fields.Int(allow_none=True)


class AdjustBottleSchema(Schema):
    new_remaining_ml = fields.Decimal(required=True)
    reason = fields.Str(required=True, validate=validate.Length(min=3, max=255))


class ReconcileSchema(Schema):
    start = fields.Str(required=True, data_key="from")
    end = fields.Str(required=True, data_key="to")
    records = fields.List(fields.Dict(), required=True)
