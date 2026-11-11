from marshmallow import Schema, fields, validate


class CreateKioskOrderSchema(Schema):
    slot_number = fields.Int(required=True, validate=validate.Range(min=1))


class RefundSchema(Schema):
    reason = fields.Str(required=True, validate=validate.Length(min=3, max=255))


class MockPaymentSchema(Schema):
    """Development only: pretend to be the payment provider."""
    payment_reference = fields.Str(required=True)
    status = fields.Str(load_default="SUCCESS", validate=validate.OneOf(["SUCCESS", "FAILED", "CANCELLED"]))
    event_id = fields.Str(allow_none=True)            # send the same event_id twice to test idempotency
    amount = fields.Decimal(allow_none=True)          # leave empty = the exact amount of the order
    currency = fields.Str(load_default="VND")


class ResolveAlertSchema(Schema):
    note = fields.Str(allow_none=True)
