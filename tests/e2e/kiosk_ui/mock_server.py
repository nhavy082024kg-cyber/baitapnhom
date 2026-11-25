"""May chu GIA (khong can MySQL) de kiem tra giao dien kiosk. Chay: python mock_server.py  (cong 5099)."""
import sys, time
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "src"))
from flask import Flask, jsonify, request
from api.controllers.kiosk_ui_controller import kiosk_ui_bp

app = Flask(__name__)
app.register_blueprint(kiosk_ui_bp)
STATE = {"orders": {}, "mode": "ok", "orderable": True}

def ok(d, c=200): return jsonify({"status": "success", "data": d}), c
def need_dev():
    return request.headers.get("X-Device-Serial") == "K1" and request.headers.get("X-Device-Secret") == "sec"

@app.get("/api/v1/kiosk/catalog")
def catalog():
    if not need_dev(): return jsonify({"status": "error", "error": {"code": "UNAUTHORIZED", "message": "bad"}}), 401
    items = [{"slot": {"slot_number": 1, "price": "50000.00", "estimated_remaining_sprays": 300, "low_stock_threshold": 20},
              "product": {"name": "Rose <b>Noir</b>", "top_notes": "Hồng", "middle_notes": "Hổ phách", "base_notes": "Xạ hương", "description": "Hương hoa hồng đêm", "usage_instructions": None}},
             {"slot": {"slot_number": 3, "price": "70000.00", "estimated_remaining_sprays": 2, "low_stock_threshold": 20},
              "product": {"name": "Oud Sauvage", "top_notes": "Trầm", "middle_notes": "Da", "base_notes": "Vani", "description": None, "usage_instructions": None}}]
    return ok({"orderable": STATE["orderable"], "reason": None if STATE["orderable"] else "Máy đang bảo trì", "items": items})

@app.post("/api/v1/kiosk/orders")
def create():
    code = "ORD-%d" % (len(STATE["orders"]) + 1)
    STATE["orders"][code] = {"status": "AWAITING_PAYMENT", "t": None}
    return ok({"order": {"order_code": code, "price": "50000.00", "status": "AWAITING_PAYMENT", "expires_at": "2099-01-01T00:00:00"},
               "payment": {"payment_reference": "SS-" + code, "qr_content": "scentstation-pay://SS-" + code}, "message": "Quét mã"}, 201)

@app.get("/api/v1/kiosk/orders/<code>")
def status(code):
    o = STATE["orders"][code]
    if o["status"] == "PAID" and time.time() - o["t"] > 3:
        o["status"] = "DISPENSED" if STATE["mode"] == "ok" else "MANUAL_REVIEW"
    return ok({"order": {"order_code": code, "status": o["status"]}, "message": "Đơn đang được xử lý"})

@app.post("/api/v1/dev/mock-payment")
def pay():
    ref = request.get_json()["payment_reference"]; code = ref[3:]
    STATE["orders"][code].update(status="PAID", t=time.time()); return ok({"result": "processed"})

@app.post("/__mode/<m>")
def mode(m):
    STATE["mode"] = m if m in ("ok", "fail") else STATE["mode"]
    if m == "blocked": STATE["orderable"] = False
    if m == "unblock": STATE["orderable"] = True
    return ok({})

app.run(port=5099)
