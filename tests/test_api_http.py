"""Kiem thu API qua HTTP (tuong duong 'unit test controller' trong bai Microsoft Web API).

Khac voi test_business_flows.py (goi thang service voi repository gia), bo test nay goi that
Flask route -> schema Marshmallow -> service -> SQLAlchemy (SQLite trong bo nho), va kiem tra
MA TRANG THAI HTTP (200/201/401/403/404/409/422), giong viec kiem Ok / NotFound trong bai MS.

Neu may chua cai SQLAlchemy/Flask thi ca file tu bo qua (skip), khong lam hong bo test cu.
Chay:  pytest tests/test_api_http.py -v
"""
import os
import uuid

import pytest

pytest.importorskip("flask")
pytest.importorskip("sqlalchemy")

os.environ["FLASK_ENV"] = "testing"          # TestingConfig: SQLite :memory:, MOCK_PAYMENT_ENABLED=True

ADMIN_EMAIL = "root@test.local"
ADMIN_PASSWORD = "Root@12345"
BRAND_PASSWORD = "Brand@12345"


@pytest.fixture(scope="module")
def client():
    from create_app import create_app
    from infrastructure.databases import get_database
    from infrastructure.databases.seed import seed_defaults

    app = create_app()
    db = get_database()
    seed_defaults(db.session, {"SEED_SUPER_ADMIN_EMAIL": ADMIN_EMAIL, "SEED_SUPER_ADMIN_PASSWORD": ADMIN_PASSWORD})
    db.session.remove()
    return app.test_client()


def uid():
    return uuid.uuid4().hex[:8]


def login(client, email, password):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def bearer(client, email, password):
    response = login(client, email, password)
    assert response.status_code == 200, response.get_data(as_text=True)
    return {"Authorization": "Bearer " + response.get_json()["data"]["access_token"]}


@pytest.fixture(scope="module")
def root(client):
    return bearer(client, ADMIN_EMAIL, ADMIN_PASSWORD)


def make_brand(client, root):
    """Tao 1 brand + 1 Brand Admin, tra ve (tenant_id, header dang nhap cua Brand Admin)."""
    code = "t" + uid()
    tenant = client.post("/api/v1/tenants", json={"name": "Brand " + code, "code": code}, headers=root)
    assert tenant.status_code == 201, tenant.get_data(as_text=True)
    tenant_id = tenant.get_json()["data"]["id"]
    email = f"admin@{code}.test"
    user = client.post("/api/v1/users", headers=root, json={
        "email": email, "password": BRAND_PASSWORD, "full_name": "Admin " + code,
        "role_codes": ["BRAND_ADMIN"], "tenant_id": tenant_id})
    assert user.status_code == 201, user.get_data(as_text=True)
    return tenant_id, bearer(client, email, BRAND_PASSWORD)


# ---------------------------------------------------------------- dang nhap / xac thuc
def test_login_ok_returns_token_and_roles(client):
    response = login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    data = response.get_json()["data"]
    assert response.status_code == 200
    assert data["token_type"] == "Bearer" and data["access_token"]
    assert "SUPER_ADMIN" in data["roles"]


def test_login_wrong_password_is_401(client):
    response = login(client, ADMIN_EMAIL, "sai-mat-khau")
    assert response.status_code == 401
    assert response.get_json()["status"] == "error"


def test_login_missing_fields_is_422(client):
    response = client.post("/api/v1/auth/login", json={})
    assert response.status_code == 422
    assert response.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_protected_endpoint_without_token_is_401(client):
    assert client.get("/api/v1/tenants").status_code == 401


def test_garbage_token_is_401(client):
    assert client.get("/api/v1/tenants", headers={"Authorization": "Bearer abc.def.ghi"}).status_code == 401


# ---------------------------------------------------------------- brand (tenant)
def test_create_tenant_201_then_duplicate_code_409(client, root):
    code = "b" + uid()
    first = client.post("/api/v1/tenants", json={"name": "Brand", "code": code}, headers=root)
    again = client.post("/api/v1/tenants", json={"name": "Brand", "code": code}, headers=root)
    assert first.status_code == 201
    assert again.status_code == 409
    assert again.get_json()["error"]["code"] == "CONFLICT"


@pytest.mark.parametrize("body", [{"name": "X"}, {"code": "x"}, {"name": "Brand", "code": "Ma Sai!"}])
def test_create_tenant_invalid_body_is_422(client, root, body):
    assert client.post("/api/v1/tenants", json=body, headers=root).status_code == 422


def test_request_body_must_be_one_json_object(client, root):
    """Loi that da gap: dan 5 dong JSON lien nhau vao mot body."""
    raw = '{"name":"A","code":"aa"}\n{"name":"B","code":"bb"}'
    response = client.post("/api/v1/tenants", data=raw, content_type="application/json", headers=root)
    assert response.status_code == 422


def test_brand_admin_cannot_list_all_brands(client, root):
    _, brand = make_brand(client, root)
    assert client.get("/api/v1/tenants", headers=brand).status_code == 403


# ---------------------------------------------------------------- cach ly du lieu giua cac brand
def test_tenant_isolation_other_brand_gets_404(client, root):
    _, brand_a = make_brand(client, root)
    _, brand_b = make_brand(client, root)
    created = client.post("/api/v1/products", headers=brand_a, json={
        "sku": "SKU-" + uid(), "name": "Secret Scent", "default_price_per_spray": "50000"})
    assert created.status_code == 201, created.get_data(as_text=True)
    product_id = created.get_json()["data"]["id"]

    assert client.get(f"/api/v1/products/{product_id}", headers=brand_a).status_code == 200
    assert client.get(f"/api/v1/products/{product_id}", headers=brand_b).status_code == 404
    listing_b = client.get("/api/v1/products", headers=brand_b).get_json()["data"]
    assert all(p["id"] != product_id for p in listing_b)


# ---------------------------------------------------------------- kiosk / thiet bi
def test_kiosk_requires_valid_device_credentials(client):
    assert client.get("/api/v1/kiosk/catalog").status_code == 401
    bad = {"X-Device-Serial": "KHONG-CO", "X-Device-Secret": "sai"}
    assert client.get("/api/v1/kiosk/catalog", headers=bad).status_code == 401


def test_mock_payment_unknown_reference_does_not_crash(client):
    response = client.post("/api/v1/dev/mock-payment", json={"payment_reference": "PAY-KHONG-CO"})
    assert response.status_code < 500


# ---------------------------------------------------------------- luong ban hang day du qua HTTP
def build_kiosk(client, root):
    """Brand + san pham + may 4 slot + chai da lap vao slot 1. Tra ve (header brand, device headers)."""
    _, brand = make_brand(client, root)
    product = client.post("/api/v1/products", headers=brand, json={
        "sku": "SKU-" + uid(), "name": "Rose", "default_price_per_spray": "50000"}).get_json()["data"]
    serial = "KIOSK-" + uid().upper()
    registered = client.post("/api/v1/machines", headers=brand, json={"serial_number": serial, "slot_count": 4})
    assert registered.status_code == 201, registered.get_data(as_text=True)
    machine = registered.get_json()["data"]
    device = {"X-Device-Serial": serial, "X-Device-Secret": machine["device_secret"]}
    detail = client.get(f"/api/v1/machines/{machine['machine']['id']}", headers=brand).get_json()["data"]
    slot = sorted(detail["slots"], key=lambda s: s["slot_number"])[0]
    assert client.put(f"/api/v1/slots/{slot['id']}", headers=brand,
                      json={"product_id": product["id"], "price": "50000", "enabled": True}).status_code == 200
    batch = client.post("/api/v1/inventory/batches", headers=brand, json={
        "product_id": product["id"], "batch_number": "LOT-" + uid(), "quantity": 1,
        "received_date": "2026-01-01", "expiration_date": "2030-12-31"}).get_json()["data"]
    bottle = client.post("/api/v1/inventory/bottles", headers=brand, json={
        "batch_id": batch["id"], "unique_code": "BTL-" + uid(), "capacity_ml": 50, "initial_weight_g": 180}).get_json()["data"]
    installed = client.post(f"/api/v1/inventory/slots/{slot['id']}/install-bottle", headers=brand,
                            json={"bottle_id": bottle["id"], "weight_before": 180, "weight_after": 180})
    assert installed.status_code == 200, installed.get_data(as_text=True)
    assert client.post("/api/v1/device/heartbeat", headers=device, json={"firmware_version": "1.0"}).status_code == 200
    return brand, device


def test_one_payment_gives_exactly_one_spray(client, root):
    brand, device = build_kiosk(client, root)

    order = client.post("/api/v1/kiosk/orders", headers=device, json={"slot_number": 1})
    assert order.status_code == 201, order.get_data(as_text=True)
    data = order.get_json()["data"]
    reference, code = data["payment"]["payment_reference"], data["order"]["order_code"]

    # chua tra tien -> may khong co lenh xit nao
    assert client.get("/api/v1/device/commands", headers=device).get_json()["data"] == []

    # tra tien that -> dung 1 lenh
    paid = client.post("/api/v1/dev/mock-payment", json={"payment_reference": reference, "event_id": "evt-1"})
    assert paid.status_code == 200, paid.get_data(as_text=True)
    commands = client.get("/api/v1/device/commands", headers=device).get_json()["data"]
    assert len(commands) == 1 and commands[0]["slot_number"] == 1

    # webhook trung -> khong sinh them lenh
    client.post("/api/v1/dev/mock-payment", json={"payment_reference": reference, "event_id": "evt-1"})
    assert len(client.get("/api/v1/device/commands", headers=device).get_json()["data"]) == 1

    # may bao da xit -> don DISPENSED
    command_id = commands[0]["command_id"]
    assert client.post(f"/api/v1/device/commands/{command_id}/ack", headers=device).status_code == 200
    assert client.post(f"/api/v1/device/commands/{command_id}/result", headers=device,
                       json={"status": "EXECUTED"}).status_code == 200
    status = client.get(f"/api/v1/kiosk/orders/{code}", headers=device).get_json()["data"]
    assert status["order"]["status"] == "DISPENSED"


def test_failed_dispense_goes_to_manual_review_and_never_resprays(client, root):
    brand, device = build_kiosk(client, root)
    data = client.post("/api/v1/kiosk/orders", headers=device, json={"slot_number": 1}).get_json()["data"]
    client.post("/api/v1/dev/mock-payment", json={"payment_reference": data["payment"]["payment_reference"]})
    command_id = client.get("/api/v1/device/commands", headers=device).get_json()["data"][0]["command_id"]
    client.post(f"/api/v1/device/commands/{command_id}/ack", headers=device)
    client.post(f"/api/v1/device/commands/{command_id}/result", headers=device,
                json={"status": "FAILED", "failure_code": "DOOR_OPEN"})
    status = client.get(f"/api/v1/kiosk/orders/{data['order']['order_code']}", headers=device).get_json()["data"]
    assert status["order"]["status"] == "MANUAL_REVIEW"
    assert client.get("/api/v1/device/commands", headers=device).get_json()["data"] == []
