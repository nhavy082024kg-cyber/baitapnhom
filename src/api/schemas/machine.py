from marshmallow import Schema, fields, validate

from domain.constants import OperatingMode


class RegisterMachineSchema(Schema):
    serial_number = fields.Str(required=True, validate=validate.Length(min=3, max=100))
    name = fields.Str(allow_none=True)
    location_id = fields.Int(allow_none=True)
    slot_count = fields.Int(load_default=4, validate=validate.Range(min=1, max=12))


class ModeSchema(Schema):
    mode = fields.Str(required=True, validate=validate.OneOf([m.value for m in OperatingMode]))
    post_test_passed = fields.Bool(load_default=False)


class ConfigureSlotSchema(Schema):
    product_id = fields.Int(allow_none=True)
    price = fields.Decimal(places=2)
    dosage_ms = fields.Int(validate=validate.Range(min=1))
    ml_per_spray = fields.Decimal(places=3)
    low_stock_threshold = fields.Int(validate=validate.Range(min=0))
    enabled = fields.Bool()


class TestSpraySchema(Schema):
    slot_number = fields.Int(required=True, validate=validate.Range(min=1))


class TelemetryItemSchema(Schema):
    event_uid = fields.Str(required=True)
    slot_number = fields.Int()
    weight_g = fields.Decimal()
    estimated_remaining = fields.Int()
    door_open = fields.Bool()
    leak_detected = fields.Bool()
    actuator_state = fields.Str()
    power_status = fields.Str()
    recorded_at = fields.Str()


class DeviceEventItemSchema(Schema):
    event_uid = fields.Str(required=True)
    event_type = fields.Str()
    error_code = fields.Str()
    payload = fields.Dict()
    recorded_at = fields.Str()


class HeartbeatSchema(Schema):
    firmware_version = fields.Str()
    telemetry = fields.List(fields.Nested(TelemetryItemSchema))
    events = fields.List(fields.Nested(DeviceEventItemSchema))


class CommandResultSchema(Schema):
    status = fields.Str(required=True, validate=validate.OneOf(["EXECUTED", "FAILED", "REJECTED"]))
    failure_code = fields.Str(allow_none=True)
    sensor_data = fields.Dict(allow_none=True)
