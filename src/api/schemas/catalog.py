from marshmallow import Schema, fields, validate


class ProductSchema(Schema):
    """Used for POST (all required fields) and PUT (partial)."""
    sku = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    name = fields.Str(required=True, validate=validate.Length(min=1, max=150))
    default_price_per_spray = fields.Decimal(required=True, places=2)
    description = fields.Str(allow_none=True)
    image_url = fields.Str(allow_none=True)
    top_notes = fields.Str(allow_none=True)
    middle_notes = fields.Str(allow_none=True)
    base_notes = fields.Str(allow_none=True)
    usage_instructions = fields.Str(allow_none=True)
    product_qr_url = fields.Str(allow_none=True)
    is_available = fields.Bool()


class LocationSchema(Schema):
    name = fields.Str(required=True, validate=validate.Length(min=1, max=150))
    address = fields.Str(allow_none=True)
    city = fields.Str(allow_none=True)