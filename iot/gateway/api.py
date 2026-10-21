# MỤC ĐÍCH: các endpoint HTTP của phần P1 (Flask Blueprint).
#
# A) HOOK CHO BROKER MQTT  (bảo vệ bằng header X-Gateway-Secret = SS_GATEWAY_SECRET)
#    POST /iot/auth    {"clientid","password"}                 -> {"result":"allow"|"deny"}
#    POST /iot/acl     {"clientid","action","topic"}           -> {"result":"allow"|"deny"}
#    POST /iot/ingest  {"clientid","topic","payload":{...}}    -> {"accepted":bool,"reason":"..."}
#         (ingest để thử gateway và để P6 kiểm thử tích hợp khi CHƯA có broker; cầu nối MQTT thật của P2 gọi thẳng gw.handle)
#
# B) QUẢN TRỊ MÁY  (bảo vệ bằng header X-Admin-Token = SS_ADMIN_TOKEN; tạm thời, sẽ thay bằng đăng nhập + phân quyền của Task 1)
#    POST /admin/tenants                         tạo brand
#    POST /admin/machines                        đăng ký máy (trả mật khẩu MQTT + khóa ký lệnh, CHỈ 1 LẦN)
#    GET  /admin/machines[?tenant=<mã>]          danh sách máy
#    GET  /admin/machines/<id>                   chi tiết 1 máy
#    POST /admin/machines/<id>/rotate-credentials  cấp lại bí mật
#    POST /admin/machines/<id>/disable | enable  tạm dừng / mở lại
#    POST /admin/machines/<id>/revoke            thu hồi vĩnh viễn (cần lý do)
# Cả hai nhóm đều TỪ CHỐI (401) khi bí mật/token chưa được cấu hình, tránh mở nhầm cổng khi quên đặt biến môi trường.
import hmac
import time

from flask import Blueprint, current_app, g, jsonify, request
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from . import registry
from .db import connect
from .gateway import Gateway, audit

bp = Blueprint("p1_gateway", __name__)


class ApiError(Exception):
    def __init__(self, status, code, message=""):
        super().__init__(message or code)
        self.status, self.code, self.message = status, code, message or code


def db():
    if "db" not in g:
        g.db = connect(current_app.config["CFG"].db_path)
    return g.db


def clock() -> int:
    return current_app.config["CLOCK"]()


def gateway() -> Gateway:
    return Gateway(db(), current_app.config["CFG"], clock)


def _secret_ok(header, expected):
    got = request.headers.get(header, "")
    return bool(expected) and hmac.compare_digest(got, expected)


def parse(model):
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError(400, "bad_request", "Cần body JSON là một object")
    try:
        return model.model_validate(data)
    except ValidationError as e:
        raise ApiError(400, "validation_error", "; ".join(f"{'.'.join(map(str, x['loc']))}: {x['msg']}"
                                                          for x in e.errors(include_url=False, include_context=False, include_input=False)))


def gateway_hook(fn):
    def wrapper(*a, **kw):
        if not _secret_ok("X-Gateway-Secret", current_app.config["CFG"].gateway_secret):
            raise ApiError(401, "bad_gateway_secret", "Sai hoặc thiếu X-Gateway-Secret")
        return fn(*a, **kw)
    wrapper.__name__ = fn.__name__
    return wrapper


def admin_only(fn):
    def wrapper(*a, **kw):
        if not _secret_ok("X-Admin-Token", current_app.config["CFG"].admin_token):
            raise ApiError(401, "unauthorized", "Sai hoặc thiếu X-Admin-Token")
        return fn(*a, **kw)
    wrapper.__name__ = fn.__name__
    return wrapper


# ====================================================================== A) hook cho broker
class AuthIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    clientid: str = Field(max_length=64)
    password: str = Field(default="", max_length=200)


class AclIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    clientid: str = Field(max_length=64)
    action: str = Field(pattern="^(publish|subscribe)$")
    topic: str = Field(max_length=200)


class IngestIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    clientid: str = Field(max_length=64)
    topic: str = Field(max_length=200)
    payload: dict | str


@bp.post("/iot/auth")
@gateway_hook
def broker_auth():
    b = parse(AuthIn)
    return jsonify({"result": "allow" if gateway().authenticate(b.clientid, b.password) else "deny"})


@bp.post("/iot/acl")
@gateway_hook
def broker_acl():
    b = parse(AclIn)
    return jsonify({"result": "allow" if gateway().authorize(b.clientid, b.action, b.topic) else "deny"})


@bp.post("/iot/ingest")
@gateway_hook
def ingest():
    import json
    b = parse(IngestIn)
    payload = b.payload if isinstance(b.payload, str) else json.dumps(b.payload)
    r = gateway().handle(b.topic, payload, b.clientid)
    return jsonify({"accepted": r.accepted, "reason": r.reason, "leaf": r.leaf, "duplicate": r.duplicate}), (200 if r.accepted else 422)


# ====================================================================== B) quản trị máy
class TenantIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=120)


class MachineIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tenant: str = Field(min_length=1, max_length=64)           # mã brand, ví dụ "dior"
    device_id: str = Field(min_length=1, max_length=64)        # số serial, ví dụ "SS-0001"
    name: str = Field(min_length=1, max_length=120)
    location: str | None = Field(default=None, max_length=200)
    slot_count: int = Field(default=5, ge=1, le=8)


class RevokeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(min_length=3, max_length=300)


def _need_machine(mid):
    m = db().execute("SELECT * FROM machines WHERE id = ?", (mid,)).fetchone()
    if m is None:
        raise ApiError(404, "not_found", "Không tìm thấy máy")
    return m


@bp.post("/admin/tenants")
@admin_only
def create_tenant():
    b = parse(TenantIn)
    tid = registry.create_tenant(db(), b.code, b.name, clock())
    audit(db(), "TENANT_CREATED", clock(), tenant_id=tid, detail={"code": b.code})
    db().commit()
    return jsonify({"id": tid, "code": b.code, "name": b.name}), 201


@bp.post("/admin/machines")
@admin_only
def register_machine():
    b = parse(MachineIn)
    mid, sec = registry.register_machine(db(), b.tenant, b.device_id, b.name, b.location, b.slot_count, clock())
    audit(db(), "MACHINE_REGISTERED", clock(), device_id=b.device_id, detail={"tenant": b.tenant, "slots": b.slot_count})
    db().commit()
    out = registry.public_machine(db().execute("SELECT * FROM machines WHERE id = ?", (mid,)).fetchone())
    out["credentials"] = sec                                   # hiển thị đúng 1 lần
    return jsonify(out), 201


@bp.get("/admin/machines")
@admin_only
def list_machines():
    tenant = request.args.get("tenant")
    q, args = "SELECT m.* FROM machines m JOIN tenants t ON t.id = m.tenant_id", []
    if tenant:
        q, args = q + " WHERE t.code = ?", [tenant]
    return jsonify([registry.public_machine(r) for r in db().execute(q + " ORDER BY m.device_id", args)])


@bp.get("/admin/machines/<mid>")
@admin_only
def get_machine(mid):
    return jsonify(registry.public_machine(_need_machine(mid)))


@bp.post("/admin/machines/<mid>/rotate-credentials")
@admin_only
def rotate(mid):
    _need_machine(mid)
    sec = registry.rotate_credentials(db(), mid, clock())
    audit(db(), "CREDENTIALS_ROTATED", clock(), device_id=_need_machine(mid)["device_id"])
    db().commit()
    return jsonify({"id": mid, "credentials": sec})


def _status(mid, status):
    _need_machine(mid)
    registry.set_status(db(), mid, status, clock())
    audit(db(), "MACHINE_" + status.upper(), clock(), device_id=_need_machine(mid)["device_id"])
    db().commit()
    return jsonify(registry.public_machine(_need_machine(mid)))


@bp.post("/admin/machines/<mid>/disable")
@admin_only
def disable(mid): return _status(mid, "disabled")


@bp.post("/admin/machines/<mid>/enable")
@admin_only
def enable(mid): return _status(mid, "active")


@bp.post("/admin/machines/<mid>/revoke")
@admin_only
def revoke(mid):
    b = parse(RevokeIn)
    _need_machine(mid)
    m = registry.revoke_machine(db(), mid, clock())
    audit(db(), "MACHINE_REVOKED", clock(), tenant_id=m["tenant_id"], device_id=m["device_id"], detail={"reason": b.reason})
    db().commit()
    return jsonify({"id": mid, "status": "revoked"})


# ====================================================================== lỗi chung
def register_errors(app):
    @app.errorhandler(ApiError)
    def on_api(e):
        return jsonify({"error": e.code, "message": e.message}), e.status

    @app.errorhandler(registry.RegistryError)
    def on_registry(e):
        status = {"not_found": 404, "tenant_not_found": 404, "device_exists": 409, "tenant_exists": 409, "machine_revoked": 409}.get(e.code, 400)
        return jsonify({"error": e.code, "message": e.message}), status
