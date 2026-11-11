from marshmallow import Schema, fields, validate


class CreateBatchSchema(Schema):
    product_id = fields.Int(required=True)
    batch_number = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    quantity = fields.Int(required=True, validate=validate.Range(min=1))
    received_date = fields.Date(required=True)
    expiration_date = fields.Date(allow_none=True)


class RegisterBottleSchema(Schema):
    batch_id = fields.Int(required=True)
    unique_code = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    capacity_ml = fields.Decimal(required=True)
    initial_weight_g = fields.Decimal(allow_none=True)


class InstallBottleSchema(Schema):
    bottle_id = fields.Int(required=True)
    weight_before = fields.Decimal(allow_none=True)
    weight_after = fields.Decimal(allow_none=True)
