# MỤC ĐÍCH: quy ước tên topic MQTT mà gateway cần để kiểm tra tin nhắn.
#   Dạng topic:  ss/<mã_brand>/<serial_máy>/<leaf>
#     Máy -> cloud (uplink)  : telemetry, event, ack, result
#     Cloud -> máy (downlink): cmd, result_ack
#   parse_topic(t)  -> (tenant_code, device_id, leaf) hoặc None nếu sai dạng.
#   make_topic(...) -> ghép chuỗi topic.
# Lưu ý cho P2 (MQTT): nếu nhóm thống nhất đổi quy ước topic thì chỉ cần sửa file này.
# Mỗi đoạn chỉ được chứa chữ, số và . _ : - (tối đa 64 ký tự) để không chèn được '/', '+', '#' (ký tự đại diện MQTT).
import re

ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,64}$")
UPLINK_LEAVES = ("telemetry", "event", "ack", "result")      # thiết bị được phép PUBLISH
DOWNLINK_LEAVES = ("cmd", "result_ack")                      # thiết bị được phép SUBSCRIBE


def valid_id(s) -> bool:
    return isinstance(s, str) and bool(ID_RE.match(s))


def make_topic(tenant_code: str, device_id: str, leaf: str) -> str:
    return f"ss/{tenant_code}/{device_id}/{leaf}"


def parse_topic(t):
    """ss/<tenant_code>/<device_id>/<leaf> -> (tenant_code, device_id, leaf) hoặc None."""
    if not isinstance(t, str):
        return None
    parts = t.split("/")
    if len(parts) != 4 or parts[0] != "ss" or not all(valid_id(p) for p in parts[1:]):
        return None
    return parts[1], parts[2], parts[3]
