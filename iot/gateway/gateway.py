# MỤC ĐÍCH: nhận mọi tin nhắn từ máy kiosk, kiểm tra an toàn, rồi chuyển cho phần xử lý tương ứng.
#
# Gateway KHÔNG biết gì về MQTT. Nó nhận (topic, payload, client_id) từ bất kỳ nguồn nào:
#   - cầu nối MQTT của P2 (gọi gw.handle(...) mỗi khi broker có tin),
#   - endpoint HTTP /iot/ingest (dùng để thử và để P6 kiểm thử tích hợp khi chưa có broker).
#
# QUY TRÌNH gw.handle() (dừng ở lỗi đầu tiên, không thay đổi dữ liệu, ghi gateway_audit):
#   1 BAD_TOPIC          topic sai dạng ss/<brand>/<serial>/<leaf> hoặc leaf không phải loại máy được gửi
#   2 UNKNOWN_DEVICE     serial chưa đăng ký
#   3 IDENTITY_MISMATCH  client id đã xác thực ở broker khác serial trong topic (máy A giả máy B)
#   4 DEVICE_REVOKED     máy đã bị thu hồi
#   5 TENANT_MISMATCH    mã brand trong topic khác brand thật của máy
#   6 TENANT_SUSPENDED   brand đang bị khóa
#   7 PAYLOAD_TOO_LARGE  quá giới hạn kích thước
#   8 BAD_PAYLOAD        không phải JSON hợp lệ hoặc sai schema của loại tin đó (schemas.py)
# Sau đó:
#   - cập nhật last_seen_at (mọi tin hợp lệ là dấu hiệu máy còn sống),
#   - tin "event": lưu vào device_events, trùng event id thì bỏ qua (an toàn khi broker gửi lặp, QoS 1),
#   - gọi handler do phần khác đăng ký (xem register_handler).
#
# ĐIỂM NỐI CHO CÁC PHẦN KHÁC (không cần sửa file này):
#   gw.register_handler("telemetry", fn)   # P3 giám sát
#   gw.register_handler("ack", fn)         # P4 lệnh từ xa
#   gw.register_handler("result", fn)      # P4 lệnh từ xa
#   gw.register_handler("event", fn)       # (tùy chọn) P5 cảnh báo muốn nghe sự kiện mới
#   fn(db, msg) nhận đối tượng Message (msg.machine, msg.body, msg.now...). Lỗi trong handler không làm gateway chết:
#   gateway rollback phần handler, ghi audit HANDLER_ERROR và vẫn trả "accepted".
#
# QUY TẮC TIN CẬY: danh tính thiết bị lấy từ client id đã xác thực ở broker + sổ đăng ký, KHÔNG lấy từ nội dung tin.
# Brand của mọi dòng dữ liệu lấy từ sổ đăng ký (msg.machine["tenant_id"]), không lấy từ topic.
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from pydantic import ValidationError

from . import registry, topics
from .config import Config
from .schemas import MODELS

log = logging.getLogger("gateway")


@dataclass
class Message:
    """Tin nhắn đã qua toàn bộ kiểm tra, đưa cho handler."""
    leaf: str                 # telemetry | event | ack | result
    machine: Any              # dòng bảng machines + tenant_code, tenant_status
    body: Any                 # đối tượng pydantic đã kiểm tra (TelemetryT, EventT, AckT, ResultT)
    now: int                  # thời điểm nhận (giây Unix)
    duplicate: bool = False   # chỉ có ý nghĩa với "event": True nếu event id đã lưu trước đó


@dataclass
class Result:
    accepted: bool
    reason: str = ""          # mã từ chối khi accepted = False
    leaf: str = ""
    duplicate: bool = False
    outbound: list = field(default_factory=list)   # [(topic, json_str)] handler có thể yêu cầu phát lại cho máy (P2 phát)


def audit(db, action, now, tenant_id=None, device_id=None, detail=None):
    """Ghi nhật ký; người gọi tự commit."""
    if detail is not None and not isinstance(detail, str):
        detail = json.dumps(detail, sort_keys=True, default=str)
    db.execute("INSERT INTO gateway_audit(ts,action,tenant_id,device_id,detail) VALUES (?,?,?,?,?)",
               (now, action, tenant_id, device_id, (detail or "")[:400]))


class Gateway:
    def __init__(self, db, cfg: Config | None = None, clock: Callable[[], int] | None = None):
        self.db = db
        self.cfg = cfg or Config()
        self.clock = clock or (lambda: int(time.time()))
        self._handlers: dict[str, list[Callable]] = {leaf: [] for leaf in topics.UPLINK_LEAVES}

    # ------------------------------------------------------------ điểm nối cho P3/P4/P5
    def register_handler(self, leaf: str, fn: Callable) -> None:
        if leaf not in self._handlers:
            raise ValueError(f"leaf phải là một trong {topics.UPLINK_LEAVES}")
        self._handlers[leaf].append(fn)

    # ------------------------------------------------------------ hook của broker
    def authenticate(self, client_id, password) -> bool:
        """Broker hỏi: client này có được kết nối không?"""
        return registry.authenticate(self.db, client_id, password) is not None

    def authorize(self, client_id, action, topic) -> bool:
        """ACL: máy chỉ được PUBLISH topic uplink của chính nó và SUBSCRIBE topic downlink của chính nó."""
        p = topics.parse_topic(topic)
        m = registry.machine_by_device(self.db, client_id)
        if not p or not m or m["status"] == "revoked" or p[0] != m["tenant_code"] or p[1] != client_id:
            return False
        if action == "publish":
            return p[2] in topics.UPLINK_LEAVES
        if action == "subscribe":
            return p[2] in topics.DOWNLINK_LEAVES
        return False

    # ------------------------------------------------------------ nhận tin từ máy
    def _reject(self, m, reason, topic, now, client_id=None):
        audit(self.db, "DEVICE_MESSAGE_REJECTED", now, tenant_id=m["tenant_id"] if m else None,
              device_id=(m["device_id"] if m else (client_id or "")[:64]), detail={"reason": reason, "topic": str(topic)[:120]})
        self.db.commit()
        return Result(False, reason)

    def handle(self, topic: str, payload, client_id: str) -> Result:
        now = self.clock()
        p = topics.parse_topic(topic)
        if not p or p[2] not in topics.UPLINK_LEAVES:
            return self._reject(None, "BAD_TOPIC", topic, now, client_id)
        tenant_code, device_id, leaf = p
        m = registry.machine_by_device(self.db, device_id)
        if m is None:
            return self._reject(None, "UNKNOWN_DEVICE", topic, now, client_id)
        if client_id != device_id:
            return self._reject(m, "IDENTITY_MISMATCH", topic, now)
        if m["status"] == "revoked":
            return self._reject(m, "DEVICE_REVOKED", topic, now)
        if tenant_code != m["tenant_code"]:
            return self._reject(m, "TENANT_MISMATCH", topic, now)
        if str(m["tenant_status"]).lower() != "active":      # so sánh không phân biệt hoa thường: khớp bảng tenants của nhóm (chữ thường)
            return self._reject(m, "TENANT_SUSPENDED", topic, now)
        if isinstance(payload, str):
            payload = payload.encode()
        if not isinstance(payload, (bytes, bytearray)) or len(payload) > self.cfg.max_payload_bytes:
            return self._reject(m, "PAYLOAD_TOO_LARGE", topic, now)
        try:
            body = MODELS[leaf].model_validate(json.loads(payload))
        except (ValueError, ValidationError):
            return self._reject(m, "BAD_PAYLOAD", topic, now)

        # Tin hợp lệ: ghi nhận máy còn sống (và lưu sự kiện), rồi commit TRƯỚC khi gọi handler của phần khác.
        self.db.execute("UPDATE machines SET last_seen_at = ?, updated_at = ? WHERE id = ?", (now, now, m["id"]))
        msg = Message(leaf=leaf, machine=m, body=body, now=now)
        if leaf == "event":
            msg.duplicate = self._store_event(m, body, now)
        self.db.commit()
        out = Result(True, leaf=leaf, duplicate=msg.duplicate)

        if not msg.duplicate:                                  # tin trùng: không chạy lại tác dụng phụ
            for fn in self._handlers[leaf]:
                try:
                    res = fn(self.db, msg)
                    if res:                                    # handler có thể trả [(topic, payload)] cần phát cho máy
                        out.outbound.extend(res)
                    self.db.commit()
                except Exception:
                    self.db.rollback()
                    log.exception("handler %s lỗi với tin %s của %s", getattr(fn, "__name__", fn), leaf, device_id)
                    audit(self.db, "HANDLER_ERROR", now, tenant_id=m["tenant_id"], device_id=device_id,
                          detail={"leaf": leaf, "handler": getattr(fn, "__name__", "?")})
                    self.db.commit()
        return out

    def _store_event(self, m, e, now) -> bool:
        """Lưu sự kiện. Trả True nếu là tin TRÙNG (event id đã có)."""
        cur = self.db.execute("INSERT OR IGNORE INTO device_events(tenant_id,machine_id,event_id,type,detail,received_at) VALUES (?,?,?,?,?,?)",
                              (m["tenant_id"], m["id"], e.id, e.type, e.detail, now))
        if cur.rowcount == 0:
            return True
        if e.type == "STARTUP":
            self.db.execute("UPDATE machines SET last_boot_at = ? WHERE id = ?", (now, m["id"]))
        return False
