# MỤC ĐÍCH: chạy thử toàn bộ phần P1 bằng một lệnh, không cần broker MQTT:
#   python demo.py
# Kịch bản: tạo 5 brand -> đăng ký 5 máy -> máy gửi telemetry/event -> thử gửi tin giả mạo -> thu hồi 1 máy.
# Dùng CSDL tạm trong bộ nhớ thư mục tạm, xóa sau khi chạy.
import json
import os
import tempfile

from gateway.app import create_app
from gateway.config import Config
from gateway.topics import make_topic

BRANDS = [("dior", "Dior"), ("gucci", "Gucci"), ("chanel", "Chanel"), ("ysl", "YSL"), ("hermes", "Hermès")]
TELEMETRY = {"mode": "IDLE", "fw": "1.1.0", "slots": [{"weight_mg": 40000, "remaining": 400, "flags": 0}] * 5}


def main():
    with tempfile.TemporaryDirectory() as tmp:
        cfg = Config(db_path=os.path.join(tmp, "demo.db"), gateway_secret="demo-gw", admin_token="demo-admin")
        c = create_app(cfg).test_client()
        adm, hook = {"X-Admin-Token": "demo-admin"}, {"X-Gateway-Secret": "demo-gw"}
        devices = {}
        for i, (code, name) in enumerate(BRANDS, 1):
            c.post("/admin/tenants", json={"code": code, "name": name}, headers=adm)
            r = c.post("/admin/machines", json={"tenant": code, "device_id": f"SS-000{i}", "name": f"{name} kiosk"}, headers=adm).get_json()
            devices[code] = (r["device_id"], r["credentials"]["mqtt_password"], r["id"])
            print(f"đăng ký {r['device_id']} cho {name}")

        print("\n-- máy đăng nhập broker (hook /iot/auth)")
        did, pw, _ = devices["dior"]
        print("đúng mật khẩu :", c.post("/iot/auth", json={"clientid": did, "password": pw}, headers=hook).get_json())
        print("sai mật khẩu  :", c.post("/iot/auth", json={"clientid": did, "password": "sai"}, headers=hook).get_json())

        print("\n-- máy gửi tin (qua /iot/ingest, giống như cầu nối MQTT gọi gateway)")
        for code, (dev, _, _) in devices.items():
            r = c.post("/iot/ingest", json={"clientid": dev, "topic": make_topic(code, dev, "telemetry"), "payload": TELEMETRY}, headers=hook)
            print(f"{code:7s} telemetry ->", r.get_json()["accepted"])
        ev = {"clientid": did, "topic": make_topic("dior", did, "event"), "payload": {"id": "SS-0001-1-1", "type": "STARTUP"}}
        print("event lần 1 ->", c.post("/iot/ingest", json=ev, headers=hook).get_json())
        print("event lần 2 (gửi lặp) ->", c.post("/iot/ingest", json=ev, headers=hook).get_json())

        print("\n-- tin giả mạo bị chặn")
        gucci = devices["gucci"][0]
        for label, body in (
            ("máy Dior giả làm máy Gucci", {"clientid": did, "topic": make_topic("gucci", gucci, "telemetry"), "payload": TELEMETRY}),
            ("máy Dior gửi vào topic brand khác", {"clientid": did, "topic": make_topic("gucci", did, "telemetry"), "payload": TELEMETRY}),
            ("JSON sai schema", {"clientid": did, "topic": make_topic("dior", did, "telemetry"), "payload": {"mode": "BOOM"}}),
            ("máy lạ", {"clientid": "SS-HACK", "topic": make_topic("dior", "SS-HACK", "telemetry"), "payload": TELEMETRY}),
        ):
            print(f"{label:35s} ->", c.post("/iot/ingest", json=body, headers=hook).get_json()["reason"])

        print("\n-- thu hồi máy Hermès")
        mid = devices["hermes"][2]
        print(c.post(f"/admin/machines/{mid}/revoke", json={"reason": "máy bị mất cắp"}, headers=adm).get_json())
        hd = devices["hermes"][0]
        r = c.post("/iot/ingest", json={"clientid": hd, "topic": make_topic("hermes", hd, "telemetry"), "payload": TELEMETRY}, headers=hook)
        print("tin sau khi thu hồi ->", r.get_json()["reason"])
        print("\nDanh sách máy:", json.dumps([(m["device_id"], m["status"]) for m in c.get("/admin/machines", headers=adm).get_json()]))


if __name__ == "__main__":
    main()
