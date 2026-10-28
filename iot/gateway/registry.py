# MỤC ĐÍCH: sổ đăng ký máy và danh tính thiết bị.
#   create_tenant(...)        : tạo brand (bản tối thiểu để P1 chạy độc lập)
#   register_machine(...)     : đăng ký máy cho 1 brand, sinh 2 bí mật HIỂN THỊ ĐÚNG 1 LẦN:
#                               mqtt_password (máy dùng đăng nhập broker) và command_key_hex (khóa ký lệnh, P4 dùng)
#   issue_credentials(...)    : cấp mới/xoay bí mật (cái cũ mất hiệu lực ngay)
#   set_status(...)           : active <-> disabled (tạm dừng máy)
#   revoke_machine(...)       : thu hồi vĩnh viễn (máy bị mất cắp/xâm nhập); mọi tin sau đó bị từ chối
#   authenticate(...)         : broker hỏi "client này có đúng mật khẩu không?"
#   machine_by_device(...)    : tra máy theo serial, kèm mã và trạng thái brand
#   command_key(...)          : lấy khóa ký lệnh (chỉ P4 gọi)
# Bảo mật: mật khẩu chỉ lưu dạng băm; so sánh bằng hmac.compare_digest; máy không tồn tại, sai mật khẩu và bị
# thu hồi đều trả cùng kết quả "không xác thực" với thời gian xử lý tương tự (không lộ máy nào có tồn tại).
import hashlib
import hmac
import secrets
import uuid

from .topics import valid_id


class RegistryError(Exception):
    """Lỗi nghiệp vụ; code ngắn gọn để API đổi thành mã HTTP."""
    def __init__(self, code, message=""):
        super().__init__(message or code)
        self.code, self.message = code, message or code


def _new_id() -> str:
    return str(uuid.uuid4())


def _hash_secret(s: str) -> str:
    # Bí mật là 256 bit ngẫu nhiên nên băm nhanh SHA-256 là đủ (được kiểm tra ở mỗi lần máy kết nối).
    return hashlib.sha256(s.encode()).hexdigest()


# ---------------------------------------------------------------- brand
def create_tenant(db, code, name, now):
    if not valid_id(code):
        raise RegistryError("bad_tenant_code", "Mã brand chỉ gồm chữ, số và . _ : - (tối đa 64 ký tự)")
    tid = _new_id()
    try:
        db.execute("INSERT INTO tenants(id,code,name,created_at) VALUES (?,?,?,?)", (tid, code, name, now))
    except Exception as e:                                   # sqlite3.IntegrityError
        raise RegistryError("tenant_exists", "Mã brand đã tồn tại") from e
    return tid


def tenant_by_code(db, code):
    return db.execute("SELECT * FROM tenants WHERE code = ?", (code,)).fetchone()


# ---------------------------------------------------------------- máy
def register_machine(db, tenant_code, device_id, name, location, slot_count, now):
    """Trả về (machine_id, secrets). secrets chỉ có ở lần gọi này, không lấy lại được."""
    if not valid_id(device_id):
        raise RegistryError("bad_device_id", "device_id chỉ gồm chữ, số và . _ : - (tối đa 64 ký tự)")
    if not 1 <= slot_count <= 8:
        raise RegistryError("bad_slot_count", "slot_count phải từ 1 đến 8")
    t = tenant_by_code(db, tenant_code)
    if t is None:
        raise RegistryError("tenant_not_found", "Brand không tồn tại")
    mid = _new_id()
    try:
        db.execute("INSERT INTO machines(id,tenant_id,device_id,name,location,slot_count,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)",
                   (mid, t["id"], device_id, name, location, slot_count, now, now))
    except Exception as e:                                   # serial đã đăng ký (bởi bất kỳ brand nào)
        raise RegistryError("device_exists", "Số serial đã được đăng ký") from e
    return mid, issue_credentials(db, mid, t["id"], now)


def issue_credentials(db, machine_id, tenant_id, now):
    mqtt_secret, key_hex = secrets.token_urlsafe(32), secrets.token_hex(32)
    db.execute("DELETE FROM device_credentials WHERE machine_id = ?", (machine_id,))
    db.execute("INSERT INTO device_credentials(machine_id,tenant_id,mqtt_secret_hash,command_key_hex,created_at) VALUES (?,?,?,?,?)",
               (machine_id, tenant_id, _hash_secret(mqtt_secret), key_hex, now))
    return {"mqtt_password": mqtt_secret, "command_key_hex": key_hex}


def rotate_credentials(db, machine_id, now):
    m = db.execute("SELECT * FROM machines WHERE id = ?", (machine_id,)).fetchone()
    if m is None:
        raise RegistryError("not_found", "Không tìm thấy máy")
    if m["status"] == "revoked":
        raise RegistryError("machine_revoked", "Máy đã bị thu hồi")
    return issue_credentials(db, machine_id, m["tenant_id"], now)


def set_status(db, machine_id, status, now):
    """active <-> disabled. Máy revoked không thể bật lại."""
    if status not in ("active", "disabled"):
        raise RegistryError("bad_status")
    m = db.execute("SELECT * FROM machines WHERE id = ?", (machine_id,)).fetchone()
    if m is None:
        raise RegistryError("not_found", "Không tìm thấy máy")
    if m["status"] == "revoked":
        raise RegistryError("machine_revoked", "Máy đã bị thu hồi")
    db.execute("UPDATE machines SET status = ?, updated_at = ? WHERE id = ?", (status, now, machine_id))


def revoke_machine(db, machine_id, now):
    m = db.execute("SELECT * FROM machines WHERE id = ?", (machine_id,)).fetchone()
    if m is None:
        raise RegistryError("not_found", "Không tìm thấy máy")
    db.execute("UPDATE device_credentials SET revoked_at = ? WHERE machine_id = ? AND revoked_at IS NULL", (now, machine_id))
    db.execute("UPDATE machines SET status = 'revoked', updated_at = ? WHERE id = ?", (now, machine_id))
    return m


# ---------------------------------------------------------------- tra cứu / xác thực
def authenticate(db, client_id, password):
    """Hook xác thực của broker. Trả về dòng máy nếu đúng, ngược lại None (không phân biệt lý do)."""
    row = db.execute("SELECT m.*, c.mqtt_secret_hash, c.revoked_at FROM machines m JOIN device_credentials c ON c.machine_id = m.id"
                     " WHERE m.device_id = ?", (client_id,)).fetchone()
    stored = row["mqtt_secret_hash"] if row else _hash_secret("x")       # máy lạ vẫn tốn thời gian xử lý như máy thật
    ok = hmac.compare_digest(stored, _hash_secret(password or ""))
    if not row or not ok or row["revoked_at"] is not None or row["status"] == "revoked":
        return None
    return row


def machine_by_device(db, device_id):
    return db.execute("SELECT m.*, t.code AS tenant_code, t.status AS tenant_status FROM machines m JOIN tenants t ON t.id = m.tenant_id"
                      " WHERE m.device_id = ?", (device_id,)).fetchone()


def command_key(db, machine_id) -> str:
    """Khóa ký lệnh của máy (P4 dùng để ký lệnh gửi xuống). Máy bị thu hồi thì không có khóa."""
    row = db.execute("SELECT command_key_hex FROM device_credentials WHERE machine_id = ? AND revoked_at IS NULL", (machine_id,)).fetchone()
    if row is None:
        raise RegistryError("no_credentials", "Máy không có khóa còn hiệu lực")
    return row[0]


def public_machine(m):
    """Thông tin máy trả ra API: KHÔNG bao giờ gồm mật khẩu hay khóa."""
    return {"id": m["id"], "tenant_id": m["tenant_id"], "device_id": m["device_id"], "name": m["name"], "location": m["location"],
            "status": m["status"], "slot_count": m["slot_count"], "last_seen_at": m["last_seen_at"], "last_boot_at": m["last_boot_at"]}
