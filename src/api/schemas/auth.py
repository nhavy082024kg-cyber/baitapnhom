from marshmallow import Schema, fields, validate


class LoginSchema(Schema):
    email = fields.Email(required=True)
    password = fields.Str(required=True)


class StepUpSchema(Schema):
    password = fields.Str(required=True)
