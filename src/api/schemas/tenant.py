from marshmallow import Schema, fields, validate

from domain.constants import TenantStatus, UserStatus


class CreateTenantSchema(Schema):
    name = fields.Str(required=True, validate=validate.Length(min=2, max=150))
    code = fields.Str(required=True, validate=validate.Length(min=2, max=50))
    description = fields.Str(allow_none=True)
    contact_email = fields.Email(allow_none=True)
    contact_phone = fields.Str(allow_none=True)
    logo_url = fields.Str(allow_none=True)


class TenantStatusSchema(Schema):
    status = fields.Str(required=True, validate=validate.OneOf([s.value for s in TenantStatus]))


class CreateUserSchema(Schema):
    email = fields.Email(required=True)
    password = fields.Str(required=True, validate=validate.Length(min=8))
    full_name = fields.Str(required=True, validate=validate.Length(min=2, max=150))
    role_codes = fields.List(fields.Str(), required=True)
    tenant_id = fields.Int(allow_none=True)          # only the Super Admin needs it
    phone = fields.Str(allow_none=True)


class UserStatusSchema(Schema):
    status = fields.Str(required=True, validate=validate.OneOf([s.value for s in UserStatus]))
