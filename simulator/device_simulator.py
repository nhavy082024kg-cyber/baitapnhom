#!/usr/bin/env python3
""" ScentStation kiosk simulator

- Nó hoạt động giống như cách firmware thực tế phải hoạt động:
 + Gửi một heartbeat sau mỗi vài giây.
 + Lấy các commands, xác minh signature / expiry / serial / duplicates (từ chối các lệnh không hợp lệ).
 + Từ chối xịt (spray) khi cửa đang mở (door is open) hoặc máy đang ở chế độ bảo trì (maintenance) đối với các lệnh SALE.
 + Gửi ACK cho command trước, sau đó thực hiện xịt (spray), rồi báo cáo kết quả (result).
- Cách sử dụng (sau khi đăng ký máy trong portal và sao chép device_secret):
python device_simulator.py --serial KIOSK-001 --secret <device_secret>
- Fault injection (giả lập lỗi):
 + --door-open: cửa đang mở → Các lệnh SALE bị REJECTED (thanh toán thành công, nhưng thao tác phun bị từ chối → cần manual review).
 + --fail: actuator gặp lỗi → kết quả là FAILED.
 + --no-ack: không bao giờ gửi ACK (command bị timeout và được xác định là một lỗi chắc chắn – certain failure).
 + --no-result: gửi ACK nhưng không bao giờ báo cáo kết quả (result) (command bị timeout và được xác định là trạng thái không chắc chắn – UNCERTAIN).


"""
import argparse
import hashlib
import hmac
import json
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone


class Api:
    def __init__(self, base_url, serial, secret):
        self.base_url, self.serial, self.secret = base_url.rstrip("/"), serial, secret

    def call(self, method, path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(self.base_url + path, data=data, method=method, headers={
            "Content-Type": "application/json", "X-Device-Serial": self.serial, "X-Device-Secret": self.secret})
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return response.status, json.loads(response.read() or b"{}")
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read() or b"{}")
        except urllib.error.URLError as exc:
            return 0, {"error": str(exc)}


def verify_command(command, serial, secret, seen):
    """Device-side safety rules: returns None if the command is acceptable, otherwise the reason."""
    message = f"{command['command_id']}|{command['machine_serial']}|{command['slot_number']}|{command['type']}|{command['expires_at']}"
    expected = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, command["signature"]):
        return "BAD_SIGNATURE"
    if command["machine_serial"] != serial:
        return "WRONG_MACHINE"
    if datetime.fromisoformat(command["expires_at"]) <= datetime.now(timezone.utc).replace(tzinfo=None):
        return "EXPIRED"
    if command["command_id"] in seen:
        return "DUPLICATE"
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base-url", default="http://localhost:9999")
    parser.add_argument("--serial", required=True)
    parser.add_argument("--secret", required=True)
    parser.add_argument("--heartbeat", type=float, default=5.0, help="seconds between heartbeats")
    parser.add_argument("--door-open", action="store_true")
    parser.add_argument("--fail", action="store_true")
    parser.add_argument("--no-ack", action="store_true")
    parser.add_argument("--no-result", action="store_true")
    args = parser.parse_args()

    api = Api(args.base_url, args.serial, args.secret)
    seen, mode, last_heartbeat = set(), "NORMAL", 0.0
    print(f"[sim] {args.serial} started -> {args.base_url}")

    while True:
        now = time.time()
        if now - last_heartbeat >= args.heartbeat:
            status, body = api.call("POST", "/api/v1/device/heartbeat", {
                "firmware_version": "sim-1.0.0",
                "telemetry": [{"event_uid": str(uuid.uuid4()), "door_open": args.door_open}]})
            if status == 200:
                mode = body["data"]["operating_mode"]
                print(f"[sim] heartbeat ok, mode={mode}")
            else:
                print(f"[sim] heartbeat failed: {status} {body}")
            last_heartbeat = now

        status, body = api.call("GET", "/api/v1/device/commands")
        for command in (body.get("data") or []) if status == 200 else []:
            cid = command["command_id"]
            problem = verify_command(command, args.serial, args.secret, seen)
            if problem:
                print(f"[sim] REJECT {cid[:8]}: {problem}")
                continue                                     # a forged/old command is silently dropped
            seen.add(cid)
            if args.no_ack:
                print(f"[sim] {cid[:8]} received, NOT acknowledging (fault injection)")
                continue
            api.call("POST", f"/api/v1/device/commands/{cid}/ack")
            if command["type"] == "SALE" and (args.door_open or mode != "NORMAL"):
                code = "DOOR_OPEN" if args.door_open else "MAINTENANCE_MODE"
                print(f"[sim] {cid[:8]} REFUSED: {code}")
                api.call("POST", f"/api/v1/device/commands/{cid}/result", {"status": "REJECTED", "failure_code": code})
                continue
            if args.no_result:
                print(f"[sim] {cid[:8]} acknowledged, going silent (fault injection)")
                continue
            print(f"[sim] {cid[:8]} spraying slot {command['slot_number']} for {command['dosage_ms']} ms ({command['type']})")
            time.sleep(command["dosage_ms"] / 1000)
            if args.fail:
                api.call("POST", f"/api/v1/device/commands/{cid}/result",
                         {"status": "FAILED", "failure_code": "ACTUATOR_ERROR"})
            else:
                api.call("POST", f"/api/v1/device/commands/{cid}/result", {"status": "EXECUTED"})
                print(f"[sim] {cid[:8]} done")
        time.sleep(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[sim] stopped")
