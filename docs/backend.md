# ScentStation – Backend (Flask Clean Architecture + MySQL)

Backend cho đề tài **ScentStation**: kiosk nước hoa đa thương hiệu. Xây theo khuôn Flask-CleanArchitecture
(`api → services → domain ← infrastructure`), đầu vào là `docs/ERD.md` (29 bảng).

## 1. Chạy thử

Yêu cầu: Python 3.10+, Docker (cho MySQL).

```bash
python -m venv venv && source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cd src
bash scripts/run_mysql.sh                              # MySQL 8 trong Docker 
cp .env.example .env                                   # sửa SECRET_KEY... nếu muốn
python app.py                                          # http://localhost:9999/docs
```

Lần chạy đầu tự tạo 29 bảng, 26 permission, 6 role hệ thống và tài khoản Super Admin
(`admin@scentstation.local` / `Admin@12345`, đổi trong `.env`).

Chạy test (không cần MySQL): `pytest -q` ở thư mục gốc (62 test).

Chạy bằng Docker (MySQL + backend): `docker compose up --build`, mở http://localhost:9999/docs. 

## 2. Kịch bản demo (curl hoặc Swagger `/docs`)

```text
1  POST /api/v1/auth/login                       Super Admin  -> token
2  POST /api/v1/tenants                          tạo brand
3  POST /api/v1/users                            tạo Brand Admin (kèm tenant_id)
4  login Brand Admin
5  POST /api/v1/products                         tạo nước hoa
6  POST /api/v1/machines                         đăng ký kiosk -> LƯU device_secret (chỉ hiện 1 lần)
7  PUT  /api/v1/slots/{slot_id}                  gán nước hoa + giá cho slot 1
8  POST /api/v1/inventory/batches + /bottles     nhập lô, đăng ký chai
9  POST /api/v1/inventory/slots/{id}/install-bottle   lắp chai vào slot
10 python simulator/device_simulator.py --serial <serial> --secret <device_secret>
11 POST /api/v1/kiosk/orders  {"slot_number":1}  (header X-Device-Serial, X-Device-Secret) -> QR + payment_reference
12 POST /api/v1/dev/mock-payment {"payment_reference":"..."}   giả lập thanh toán -> simulator xịt
13 GET  /api/v1/kiosk/orders/{order_code}       DISPENSED
```

Các tình huống lỗi:

| Tình huống | Cách làm | Kết quả mong đợi |
|---|---|---|
| Webhook trùng | gọi mock-payment 2 lần với cùng `event_id` | lần 2 `duplicate_ignored`, chỉ 1 lệnh xịt |
| Sai chữ ký / sai số tiền | `POST /webhooks/payment` chữ ký sai; mock-payment với `amount` khác | 401 / 422, đơn vẫn chờ thanh toán |
| Thanh toán xong nhưng máy lỗi | chạy simulator với `--door-open` hoặc `--fail` | đơn vào `MANUAL_REVIEW`, **không** xịt lần 2 |
| Máy im lặng | simulator `--no-result`, rồi `POST /system/jobs/run` | `UNCERTAIN` → `MANUAL_REVIEW` |
| Hoàn tiền | `POST /auth/step-up`, rồi `POST /orders/{id}/refund` (Ops Manager) | `REFUNDED`; thiếu step-up thì 403 |
| Cô lập tenant | Brand B gọi `GET /products/{id}` của Brand A | 404 |

## 3. Cấu trúc 

```text
src/
├── api/                  controllers/ (13 blueprint), schemas/ (Marshmallow), middleware.py (JWT, device auth),
│                         requests.py, responses.py, routes.py, swagger.py (tự sinh từ route)
├── domain/               constants.py (enum, permission), exceptions.py, clock.py
│   └── models/           entity (dataclass), irepositories.py + iservices.py (interface),
│                         order_state_machine.py, dispense_policy.py   <- luật nghiệp vụ thuần, dễ test
├── services/             auth, tenant, user, catalog, machine, inventory, order, payment, dispensing, alert, audit
├── infrastructure/
│   ├── databases/        abstract_database, mysql, sqlite, factory_database, seed, unit_of_work
│   ├── models/           29 bảng ORM theo ERD.md
│   ├── repositories/     cài đặt interface bằng SQLAlchemy (luôn lọc tenant_id)
│   └── services/         security (bcrypt/JWT/HMAC), payment_provider (mock)
├── dependency_container.py   nơi duy nhất nối interface với lớp cụ thể
├── create_app.py / app.py / config.py / cors.py / error_handler.py / app_logging.py
tests/                    fakes.py (repo giả trong bộ nhớ), test_business_flows.py, test_static_consistency.py
simulator/                device_simulator.py (kiosk giả, chỉ dùng thư viện chuẩn)
```

Luồng một request: **Controller → Service → Interface (domain) → Repository (infrastructure) → MySQL**.
Một request = một transaction: service gọi `uow.commit()` đúng một lần ở cuối use case.




