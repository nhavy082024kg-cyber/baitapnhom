import os
import pytest
from fastapi.testclient import TestClient
# Use a clean test database
os.environ["DATABASE_URL"] = "sqlite:///./test_scentstation.db"
if os.path.exists("test_scentstation.db"):
    os.remove("test_scentstation.db")

from app.main import app
from seed import seed_database

seed_database()
client = TestClient(app)

def login(email: str, password: str) -> str:
    res = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    assert res.status_code == 200, res.text
    return res.json()["access_token"]

def test_login_invalid_credentials():
    res = client.post("/api/v1/auth/login", data={"username": "manager@chanel.com", "password": "WrongPassword"})
    assert res.status_code == 401

def test_rbac_blocks_technician_from_brand_creation():
    tech_token = login("tech@chanel.com", "Pass123!")
    res = client.post(
        "/api/v1/brands",
        json={"brand_name": "Unauthorized Brand"},
        headers={"Authorization": f"Bearer {tech_token}"},
    )
    assert res.status_code == 403

def test_multi_tenant_isolation_brands_and_perfumes():
    chanel_token = login("manager@chanel.com", "Pass123!")
    lvmh_token = login("manager@lvmh.com", "Pass123!")

    # Chanel manager only sees Chanel
    chanel_brands = client.get("/api/v1/brands", headers={"Authorization": f"Bearer {chanel_token}"}).json()
    chanel_names = [b["brand_name"] for b in chanel_brands]
    assert "Chanel" in chanel_names
    assert "Dior" not in chanel_names
    assert "YSL" not in chanel_names

    # LVMH manager only sees Dior & YSL
    lvmh_brands = client.get("/api/v1/brands", headers={"Authorization": f"Bearer {lvmh_token}"}).json()
    lvmh_names = [b["brand_name"] for b in lvmh_brands]
    assert "Dior" in lvmh_names and "YSL" in lvmh_names
    assert "Chanel" not in lvmh_names

    # Cross-tenant write attempt: LVMH manager tries to add perfume to Chanel's brand_id
    chanel_brand_id = chanel_brands[0]["brand_id"]
    attack = client.post(
        f"/api/v1/brands/{chanel_brand_id}/perfumes",
        json={"product_code": "CROSS-001", "perfume_name": "Cross Tenant Attack", "price_per_spray": 5.0},
        headers={"Authorization": f"Bearer {lvmh_token}"},
    )
    assert attack.status_code == 404

def test_super_admin_can_create_tenant():
    super_token = login("superadmin@scentstation.io", "Admin123!")
    res = client.post(
        "/api/v1/tenants",
        json={"tenant_code": "NEW_BRAND_OPS", "tenant_name": "New Partner Operator"},
        headers={"Authorization": f"Bearer {super_token}"},
    )
    assert res.status_code == 201
    assert res.json()["tenant_code"] == "NEW_BRAND_OPS"
