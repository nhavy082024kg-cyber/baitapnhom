# MỤC ĐÍCH: kiểm thử tự động phần P1, chạy độc lập (không cần broker, không cần phần P2-P6).
# CÁCH CHẠY (từ thư mục iot_gateway_p1):   python -m unittest discover -s tests -t . -v
# Mỗi test dùng một CSDL SQLite tạm và đồng hồ giả (FakeClock) nên kết quả lặp lại được.
import json
import os
import tempfile
import unittest

from gateway.app import create_app
from gateway.config import Config
from gateway.db import connect
from gateway.gateway import Gateway
from gateway.topics import make_topic, parse_topic

GW_SECRET, ADMIN = "gw-secret-for-tests", "admin-token-for-tests"
BRANDS = [("dior", "Dior"), ("gucci", "Gucci"), ("chanel", "Chanel"), ("ysl", "Yves Saint Laurent"), ("hermes", "Hermès")]
TELEMETRY = {"mode": "IDLE", "fault": "", "door": False, "leak": False, "fw": "1.1.0", "cfg": "cfg1",
             "slots": [{"weight_mg": 40000, "remaining": 400, "sales": 1, "diag": 0, "flags": 0} for _ in range(5)]}


class FakeClock:
    def __init__(self, t=1_000_000): self.t = t
    def __call__(self): return self.t
    def advance(self, s): self.t += s


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cfg = Config(db_path=os.path.join(self.tmp.name, "t.db"), gateway_secret=GW_SECRET, admin_token=ADMIN)
        self.clock = FakeClock()
        self.app = create_app(self.cfg, self.clock)
        self.c = self.app.test_client()
        self.dev = {}                                           # code -> (device_id, password)
        for code, name in BRANDS:
            self.assertEqual(self.admin("post", "/admin/tenants", {"code": code, "name": name}).status_code, 201)
        for i, (code, _) in enumerate(BRANDS, 1):
            r = self.admin("post", "/admin/machines", {"tenant": code, "device_id": f"SS-000{i}", "name": f"{code} kiosk", "location": "Mall"})
            self.assertEqual(r.status_code, 201, r.get_data(as_text=True))
            self.dev[code] = (f"SS-000{i}", r.get_json()["credentials"]["mqtt_password"], r.get_json()["id"])

    def tearDown(self):
        self.tmp.cleanup()

    # ---- trợ giúp
    def admin(self, method, url, body=None, token: str | None = ADMIN):
        return getattr(self.c, method)(url, json=body, headers={"X-Admin-Token": token} if token is not None else {})

    def hook(self, url, body, secret: str | None = GW_SECRET):
        return self.c.post(url, json=body, headers={"X-Gateway-Secret": secret} if secret is not None else {})

    def db(self): return connect(self.cfg.db_path)

    def gw(self, db): return Gateway(db, self.cfg, self.clock)

    def send(self, code, leaf, payload, client_id: str | None = None, topic: str | None = None):
        dev = self.dev[code][0]
        db = self.db()
        try:
            return self.gw(db).handle(topic or make_topic(code, dev, leaf), payload if isinstance(payload, (bytes, str)) else json.dumps(payload),
                                      client_id or dev)
        finally:
            db.close()

    def row(self, sql, *args):
        db = self.db()
        try:
            return db.execute(sql, args).fetchall()
        finally:
            db.close()

    def last_seen(self, code): return self.row("SELECT last_seen_at FROM machines WHERE device_id = ?", self.dev[code][0])[0][0]

    def audits(self, action="DEVICE_MESSAGE_REJECTED"): return [dict(r) for r in self.row("SELECT * FROM gateway_audit WHERE action = ?", action)]


#  đăng ký máy và quản trị
class RegistryTests(Base):
    def test_registration_shows_secrets_once_and_never_again(self):
        r = self.admin("post", "/admin/machines", {"tenant": "dior", "device_id": "SS-9000", "name": "Spare", "slot_count": 5})
        cred = r.get_json()["credentials"]
        self.assertEqual(len(cred["command_key_hex"]), 64)
        self.assertGreaterEqual(len(cred["mqtt_password"]), 32)
        mid = r.get_json()["id"]
        for url in (f"/admin/machines/{mid}", "/admin/machines"):
            text = self.admin("get", url).get_data(as_text=True)
            self.assertNotIn(cred["mqtt_password"], text)
            self.assertNotIn(cred["command_key_hex"], text)
            self.assertNotIn("credentials", text)
        stored = self.row("SELECT mqtt_secret_hash FROM device_credentials WHERE machine_id = ?", mid)[0][0]
        self.assertNotEqual(stored, cred["mqtt_password"])                    # chỉ lưu bản băm

    def test_five_brands_five_machines(self):
        r = self.admin("get", "/admin/machines").get_json()
        self.assertEqual(len(r), 5)
        self.assertEqual([m["device_id"] for m in r], [f"SS-000{i}" for i in range(1, 6)])
        self.assertEqual(len(self.admin("get", "/admin/machines?tenant=hermes").get_json()), 1)

    def test_admin_endpoints_need_the_token(self):
        for token in (None, "wrong"):
            self.assertEqual(self.admin("get", "/admin/machines", token=token).status_code, 401)
            self.assertEqual(self.admin("post", "/admin/tenants", {"code": "x1", "name": "X"}, token=token).status_code, 401)

    def test_unconfigured_secrets_deny_everything(self):
        app = create_app(Config(db_path=os.path.join(self.tmp.name, "u.db"), gateway_secret="", admin_token=""), self.clock)
        c = app.test_client()
        self.assertEqual(c.get("/admin/machines", headers={"X-Admin-Token": ""}).status_code, 401)
        self.assertEqual(c.post("/iot/auth", json={"clientid": "a", "password": "b"}, headers={"X-Gateway-Secret": ""}).status_code, 401)

    def test_serial_unique_and_input_validated(self):
        base = {"tenant": "gucci", "name": "Dup"}
        self.assertEqual(self.admin("post", "/admin/machines", {**base, "device_id": "SS-0001"}).status_code, 409)   # serial của Dior
        self.assertEqual(self.admin("post", "/admin/machines", {**base, "device_id": "bad/id"}).status_code, 400)
        self.assertEqual(self.admin("post", "/admin/machines", {**base, "device_id": "a|b"}).status_code, 400)
        self.assertEqual(self.admin("post", "/admin/machines", {"tenant": "nope", "device_id": "SS-7", "name": "n"}).status_code, 404)
        self.assertEqual(self.admin("post", "/admin/machines", {**base, "device_id": "SS-8", "slot_count": 9}).status_code, 400)
        self.assertEqual(self.admin("post", "/admin/tenants", {"code": "dior", "name": "again"}).status_code, 409)
        self.assertEqual(self.admin("post", "/admin/tenants", {"code": "a/b", "name": "bad"}).status_code, 400)

    def test_rotate_credentials_kills_the_old_password(self):
        did, old, mid = self.dev["dior"]
        self.assertEqual(self.hook("/iot/auth", {"clientid": did, "password": old}).get_json()["result"], "allow")
        new = self.admin("post", f"/admin/machines/{mid}/rotate-credentials").get_json()["credentials"]["mqtt_password"]
        self.assertEqual(self.hook("/iot/auth", {"clientid": did, "password": old}).get_json()["result"], "deny")
        self.assertEqual(self.hook("/iot/auth", {"clientid": did, "password": new}).get_json()["result"], "allow")

    def test_disable_enable_and_revoke_is_permanent(self):
        did, pw, mid = self.dev["chanel"]
        self.assertEqual(self.admin("post", f"/admin/machines/{mid}/disable").get_json()["status"], "disabled")
        self.assertEqual(self.admin("post", f"/admin/machines/{mid}/enable").get_json()["status"], "active")
        self.assertEqual(self.admin("post", f"/admin/machines/{mid}/revoke", {"reason": "x"}).status_code, 400)       # cần lý do
        self.assertEqual(self.admin("post", f"/admin/machines/{mid}/revoke", {"reason": "máy bị mất cắp"}).get_json()["status"], "revoked")
        self.assertEqual(self.admin("post", f"/admin/machines/{mid}/enable").status_code, 409)
        self.assertEqual(self.admin("post", f"/admin/machines/{mid}/rotate-credentials").status_code, 409)
        self.assertEqual(self.admin("post", "/admin/machines/none/revoke", {"reason": "abc"}).status_code, 404)
        self.assertTrue(self.audits("MACHINE_REVOKED"))

    def test_revoked_machine_loses_auth_acl_and_uplink(self):
        did, pw, mid = self.dev["ysl"]
        self.assertTrue(self.send("ysl", "telemetry", TELEMETRY).accepted)
        self.admin("post", f"/admin/machines/{mid}/revoke", {"reason": "bị xâm nhập"})
        self.assertEqual(self.hook("/iot/auth", {"clientid": did, "password": pw}).get_json()["result"], "deny")
        self.assertEqual(self.hook("/iot/acl", {"clientid": did, "action": "publish", "topic": make_topic("ysl", did, "telemetry")}).get_json()["result"], "deny")
        r = self.send("ysl", "telemetry", TELEMETRY)
        self.assertEqual((r.accepted, r.reason), (False, "DEVICE_REVOKED"))
        db = self.db()
        from gateway import registry
        with self.assertRaises(registry.RegistryError):
            registry.command_key(db, mid)                                      # không còn khóa ký lệnh
        db.close()


# ======================================================================== hook của broker
class BrokerHookTests(Base):
    def test_auth_hook(self):
        did, pw, _ = self.dev["dior"]
        auth = lambda cid, p: self.hook("/iot/auth", {"clientid": cid, "password": p}).get_json()["result"]
        self.assertEqual(auth(did, pw), "allow")
        self.assertEqual(auth(did, "sai-mat-khau"), "deny")
        self.assertEqual(auth("SS-NOPE", pw), "deny")
        self.assertEqual(auth(did, ""), "deny")
        self.assertEqual(auth(self.dev["gucci"][0], pw), "deny")               # mật khẩu của máy khác

    def test_hooks_need_the_shared_secret(self):
        body = {"clientid": "SS-0001", "password": "x"}
        self.assertEqual(self.hook("/iot/auth", body, secret=None).status_code, 401)
        self.assertEqual(self.hook("/iot/auth", body, secret="sai").status_code, 401)
        self.assertEqual(self.hook("/iot/acl", {"clientid": "SS-0001", "action": "publish", "topic": "x"}, secret="sai").status_code, 401)
        self.assertEqual(self.hook("/iot/auth", {"password": "x"}).status_code, 400)                                    # thiếu clientid

    def test_acl_only_own_topics(self):
        did = self.dev["dior"][0]
        acl = lambda action, topic, cid=did: self.hook("/iot/acl", {"clientid": cid, "action": action, "topic": topic}).get_json()["result"]
        for leaf in ("telemetry", "event", "ack", "result"):
            self.assertEqual(acl("publish", make_topic("dior", did, leaf)), "allow")
        for leaf in ("cmd", "result_ack"):
            self.assertEqual(acl("subscribe", make_topic("dior", did, leaf)), "allow")
            self.assertEqual(acl("publish", make_topic("dior", did, leaf)), "deny")          # máy không tự gửi lệnh cho mình
        self.assertEqual(acl("subscribe", make_topic("dior", did, "telemetry")), "deny")
        self.assertEqual(acl("publish", make_topic("dior", self.dev["gucci"][0], "telemetry")), "deny")     # serial máy khác
        self.assertEqual(acl("publish", make_topic("gucci", did, "telemetry")), "deny")                     # sai brand
        for bad in ("ss/dior/SS-0001/#", "ss/+/SS-0001/telemetry", "ss/dior/SS-0001", "#", "ss/dior/SS-0001/telemetry/x", ""):
            self.assertEqual(acl("publish", bad), "deny", bad)
            self.assertEqual(acl("subscribe", bad), "deny", bad)
        self.assertEqual(acl("publish", make_topic("dior", did, "telemetry"), cid="SS-NOPE"), "deny")


# ======================================================================== quy trình nhận tin
class GatewayTests(Base):
    def test_valid_message_marks_the_machine_alive(self):
        self.assertIsNone(self.last_seen("dior"))
        r = self.send("dior", "telemetry", TELEMETRY)
        self.assertTrue(r.accepted)
        self.assertEqual(self.last_seen("dior"), self.clock.t)
        self.clock.advance(30)
        self.assertTrue(self.send("dior", "ack", {"command_id": "c1", "accepted": True, "code": "ACCEPTED"}).accepted)
        self.assertEqual(self.last_seen("dior"), self.clock.t)
        self.assertIsNone(self.last_seen("gucci"))                              # máy khác không bị ảnh hưởng

    def test_every_reject_reason_changes_nothing_and_is_audited(self):
        did = self.dev["dior"][0]
        big = json.dumps({**TELEMETRY, "fault": "x" * 30_000})
        cases = [
            ("BAD_TOPIC", dict(topic="ss/dior/SS-0001/cmd", payload=TELEMETRY)),                    # leaf downlink
            ("BAD_TOPIC", dict(topic="ss/dior/SS-0001/../../x/telemetry", payload=TELEMETRY)),
            ("BAD_TOPIC", dict(topic="x/dior/SS-0001/telemetry", payload=TELEMETRY)),
            ("UNKNOWN_DEVICE", dict(topic="ss/dior/SS-9999/telemetry", payload=TELEMETRY, client_id="SS-9999")),
            ("IDENTITY_MISMATCH", dict(client_id=self.dev["gucci"][0], payload=TELEMETRY)),         # máy Gucci giả Dior
            ("TENANT_MISMATCH", dict(topic=make_topic("gucci", did, "telemetry"), payload=TELEMETRY)),
            ("PAYLOAD_TOO_LARGE", dict(payload=big)),
            ("BAD_PAYLOAD", dict(payload="không phải json")),
            ("BAD_PAYLOAD", dict(payload=json.dumps([1, 2]))),
            ("BAD_PAYLOAD", dict(payload={**TELEMETRY, "mode": "EXPLODING"})),
            ("BAD_PAYLOAD", dict(payload={**TELEMETRY, "slots": [{"weight_mg": "heavy"}]})),
            ("BAD_PAYLOAD", dict(payload={**TELEMETRY, "slots": [{}] * 9})),                         # nhiều slot hơn tối đa
            ("BAD_PAYLOAD", dict(payload={"mode": "IDLE", "slots": [{"flags": 999}]})),
            ("BAD_PAYLOAD", dict(payload=b"\xff\xfe")),
        ]
        for reason, kw in cases:
            before = len(self.audits())
            r = self.send("dior", "telemetry", kw.pop("payload"), **kw)
            self.assertEqual((r.accepted, r.reason), (False, reason), reason)
            self.assertEqual(len(self.audits()), before + 1, reason)
        self.assertIsNone(self.last_seen("dior"))                                # không tin nào thay đổi dữ liệu
        self.assertEqual(self.row("SELECT COUNT(*) FROM device_events")[0][0], 0)

    def test_a_device_cannot_speak_for_another_brand(self):
        # máy Dior đã xác thực (client id đúng) nhưng gửi vào topic của Gucci và của máy Gucci
        did = self.dev["dior"][0]
        self.assertEqual(self.send("dior", "event", {"id": "e1", "type": "X"}, topic=make_topic("gucci", did, "event")).reason, "TENANT_MISMATCH")
        self.assertEqual(self.send("dior", "event", {"id": "e1", "type": "X"}, topic=make_topic("gucci", self.dev["gucci"][0], "event")).reason,
                         "IDENTITY_MISMATCH")
        self.assertEqual(self.row("SELECT COUNT(*) FROM device_events")[0][0], 0)

    def test_all_five_brands_work_independently(self):
        for code, _ in BRANDS:
            self.assertTrue(self.send(code, "telemetry", TELEMETRY).accepted)
            self.assertTrue(self.send(code, "event", {"id": "same-id", "type": "STARTUP"}).accepted)     # cùng event id, khác máy: đều được lưu
        self.assertEqual(self.row("SELECT COUNT(*) FROM device_events")[0][0], 5)
        tenants = {r[0] for r in self.row("SELECT DISTINCT tenant_id FROM device_events")}
        self.assertEqual(len(tenants), 5)

    def test_suspended_brand_is_rejected(self):
        db = self.db()
        db.execute("UPDATE tenants SET status = 'suspended' WHERE code = 'gucci'")
        db.commit(); db.close()
        self.assertEqual(self.send("gucci", "telemetry", TELEMETRY).reason, "TENANT_SUSPENDED")
        self.assertTrue(self.send("dior", "telemetry", TELEMETRY).accepted)

    def test_disabled_machine_can_still_report(self):
        self.admin("post", f"/admin/machines/{self.dev['hermes'][2]}/disable")
        self.assertTrue(self.send("hermes", "telemetry", TELEMETRY).accepted)

    def test_events_are_stored_once_even_if_delivered_twice(self):
        ev = {"id": "SS-0001-1-1", "type": "STARTUP", "detail": "boot"}
        a, b = self.send("dior", "event", ev), self.send("dior", "event", ev)
        self.assertEqual((a.accepted, a.duplicate, b.accepted, b.duplicate), (True, False, True, True))
        self.assertEqual(self.row("SELECT COUNT(*) FROM device_events")[0][0], 1)
        self.assertEqual(self.row("SELECT last_boot_at FROM machines WHERE device_id = 'SS-0001'")[0][0], self.clock.t)
        self.clock.advance(60)
        self.send("dior", "event", ev)                                          # gửi lặp muộn không đổi thời điểm khởi động
        self.assertNotEqual(self.row("SELECT last_boot_at FROM machines WHERE device_id = 'SS-0001'")[0][0], self.clock.t)

    def test_unknown_fields_are_ignored_and_ids_are_length_limited(self):
        self.assertTrue(self.send("dior", "telemetry", {**TELEMETRY, "evil": {"x": 1}, "tenant_id": "other"}).accepted)
        self.assertEqual(self.send("dior", "event", {"id": "x" * 97, "type": "T"}).reason, "BAD_PAYLOAD")
        self.assertEqual(self.send("dior", "event", {"id": "", "type": "T"}).reason, "BAD_PAYLOAD")

    def test_tenant_of_stored_rows_comes_from_the_registry(self):
        self.send("dior", "event", {"id": "e1", "type": "X", "detail": "tenant_id=gucci", "tenant_id": "gucci"})
        db = self.db()
        row = db.execute("SELECT e.tenant_id, t.code FROM device_events e JOIN tenants t ON t.id = e.tenant_id").fetchone()
        db.close()
        self.assertEqual(row["code"], "dior")

    def test_string_and_bytes_payloads_are_both_accepted(self):
        self.assertTrue(self.send("dior", "telemetry", json.dumps(TELEMETRY)).accepted)
        self.assertTrue(self.send("dior", "telemetry", json.dumps(TELEMETRY).encode()).accepted)


# ======================================================================== điểm nối cho phần khác
class HandlerTests(Base):
    def run_with(self, handlers, code, leaf, payload):
        db = self.db()
        gw = self.gw(db)
        for h_leaf, fn in handlers:
            gw.register_handler(h_leaf, fn)
        try:
            return gw.handle(make_topic(code, self.dev[code][0], leaf), json.dumps(payload), self.dev[code][0])
        finally:
            db.close()

    def test_handler_receives_a_validated_message(self):
        seen = []
        self.run_with([("telemetry", lambda db, m: seen.append(m))], "gucci", "telemetry", TELEMETRY)
        self.assertEqual(len(seen), 1)
        m = seen[0]
        self.assertEqual((m.leaf, m.machine["device_id"], m.machine["tenant_code"], m.body.mode, len(m.body.slots)), ("telemetry", "SS-0002", "gucci", "IDLE", 5))

    def test_handler_not_called_for_rejected_or_duplicate_messages(self):
        calls = []
        h = lambda db, m: calls.append(m.leaf)
        self.run_with([("event", h), ("telemetry", h)], "dior", "telemetry", {"mode": "NOPE"})
        ev = {"id": "e1", "type": "T"}
        self.run_with([("event", h)], "dior", "event", ev)
        self.run_with([("event", h)], "dior", "event", ev)
        self.assertEqual(calls, ["event"])

    def test_a_crashing_handler_does_not_break_the_gateway(self):
        def boom(db, m):
            db.execute("UPDATE machines SET name = 'CORRUPTED' WHERE id = ?", (m.machine["id"],))
            raise RuntimeError("lỗi của phần khác")
        r = self.run_with([("telemetry", boom)], "dior", "telemetry", TELEMETRY)
        self.assertTrue(r.accepted)
        self.assertEqual(self.last_seen("dior"), self.clock.t)                                   # vẫn ghi nhận máy còn sống
        self.assertNotEqual(self.row("SELECT name FROM machines WHERE device_id = 'SS-0001'")[0][0], "CORRUPTED")   # phần ghi dở bị hủy
        self.assertEqual(len(self.audits("HANDLER_ERROR")), 1)

    def test_handler_can_ask_for_an_outbound_message(self):
        r = self.run_with([("result", lambda db, m: [("ss/dior/SS-0001/result_ack", json.dumps({"command_id": m.body.command_id}))])],
                          "dior", "result", {"command_id": "c9", "outcome": "OK"})
        self.assertEqual(r.outbound, [("ss/dior/SS-0001/result_ack", '{"command_id": "c9"}')])

    def test_register_handler_rejects_unknown_leaf(self):
        db = self.db()
        with self.assertRaises(ValueError):
            self.gw(db).register_handler("cmd", lambda d, m: None)
        db.close()

    def test_ack_and_result_are_validated_even_without_handlers(self):
        self.assertTrue(self.send("dior", "ack", {"command_id": "c1", "accepted": False, "code": "BAD_SIGNATURE"}).accepted)
        self.assertEqual(self.send("dior", "ack", {"command_id": "c1"}).reason, "BAD_PAYLOAD")                    # thiếu accepted
        self.assertTrue(self.send("dior", "result", {"command_id": "c1", "outcome": "UNCERTAIN", "code": "POWER_LOSS"}).accepted)
        self.assertEqual(self.send("dior", "result", {"command_id": "c1", "outcome": "MAYBE"}).reason, "BAD_PAYLOAD")


# ======================================================================== endpoint ingest (thử khi chưa có broker)
class IngestTests(Base):
    def post(self, **kw):
        return self.hook("/iot/ingest", kw)

    def test_ingest_runs_the_same_pipeline(self):
        did = self.dev["hermes"][0]
        r = self.post(clientid=did, topic=make_topic("hermes", did, "telemetry"), payload=TELEMETRY)
        self.assertEqual((r.status_code, r.get_json()["accepted"]), (200, True))
        self.assertEqual(self.last_seen("hermes"), self.clock.t)
        r = self.post(clientid="SS-0001", topic=make_topic("hermes", did, "telemetry"), payload=TELEMETRY)
        self.assertEqual((r.status_code, r.get_json()["reason"]), (422, "IDENTITY_MISMATCH"))
        r = self.post(clientid=did, topic=make_topic("hermes", did, "event"), payload="không phải json")
        self.assertEqual(r.get_json()["reason"], "BAD_PAYLOAD")

    def test_ingest_needs_the_gateway_secret(self):
        self.assertEqual(self.hook("/iot/ingest", {"clientid": "a", "topic": "b", "payload": {}}, secret="sai").status_code, 401)


class TopicTests(unittest.TestCase):
    def test_parse_and_make(self):
        self.assertEqual(parse_topic(make_topic("dior", "SS-0001", "telemetry")), ("dior", "SS-0001", "telemetry"))
        for bad in ("", None, 5, "ss/a/b", "ss/a/b/c/d", "xx/a/b/c", "ss/a b/c/d", "ss/+/c/d", "ss/a/#/d", "ss/a/b|c/d", "ss/a/" + "x" * 65 + "/d"):
            self.assertIsNone(parse_topic(bad), bad)


if __name__ == "__main__":
    unittest.main()
