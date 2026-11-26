# Kiến trúc hệ thống ScentStation
## 1. Bức tranh tổng thể

Phần cứng được thay bằng **simulator** (`simulator/device_simulator.py`) giao tiếp HTTP pull. Thanh toán là **mock** ký HMAC. Cả hai thay được bằng thật mà không sửa service nhờ interface (`IPaymentProvider`, repository).

## 2. Lớp và quy tắc phụ thuộc

| Lớp | Thư mục | Được phụ thuộc vào | Không được |
|---|---|---|---|
| API | `src/api` | services, domain | gọi repository trực tiếp, chứa luật nghiệp vụ |
| Service | `src/services` | domain (interface) | import SQLAlchemy/Flask |
| Domain | `src/domain` | chỉ thư viện chuẩn | import lớp khác |
| Infrastructure | `src/infrastructure` | domain | chứa luật nghiệp vụ |

Nối interface và lớp cụ thể chỉ ở `src/dependency_container.py`. Nhờ vậy service test được bằng repository giả trong bộ nhớ (`tests/fakes.py`) mà không cần MySQL.

## 3. Quyết định thiết kế quan trọng (ADR rút gọn)

| # | Quyết định | Lý do | Đánh đổi |
|---|---|---|---|
| 1 | Cô lập tenant bằng `tenant_id` trong mọi truy vấn, lấy từ JWT | Đơn giản, đủ cho đồ án | Phụ thuộc kỷ luật code; không cách ly cấp DB |
| 2 | Một request = một transaction (UnitOfWork) | Webhook → đơn → lệnh xịt nguyên tử | Service phải gọi `commit()` đúng một lần |
| 3 | Idempotency 3 lớp: `provider_event_id` UNIQUE, `create_sale_command` idempotent, `UNIQUE(order_id, type)` | Một thanh toán tối đa một lần xịt | Thêm ràng buộc DB |
| 4 | Không tự thử lại khi lỗi/không chắc chắn → MANUAL_REVIEW | Tránh xịt hai lần với một lần trả tiền | Cần người xử lý |
| 5 | Lệnh xịt ký HMAC, secret thiết bị = HMAC(master_key, serial), DB chỉ lưu sha256 | Thiết bị tự kiểm tra tính xác thực; lộ DB không lộ secret | Quản lý master key |
| 6 | HTTP pull thay MQTT | Không cần broker, dễ demo | Độ trễ cao hơn push; đổi MQTT sau qua service gửi lệnh |
| 7 | Chữ ký lệnh dùng `expires_at` cắt về giây | MySQL DATETIME mất micro giây làm sai chữ ký | — |
| 8 | Token JWT gắn session trong DB (`jti`) | Thu hồi được khi khóa tài khoản/logout | Thêm một lần đọc DB mỗi request |
| 9 | Tồn kho = ước tính theo số lần xịt × ml/xịt, đối chiếu cảm biến | Đúng yêu cầu đề tài | Cần hiệu chuẩn thực tế |
| 10 | Swagger sinh từ route + Marshmallow | Ít phụ thuộc, không lệch tài liệu | Ít tính năng hơn flasgger |

## 4. Dữ liệu

29 bảng, xem `ERD.md`. Nhóm bảng:
- **Định danh và quyền**: tenants, users, roles, permissions, user_roles, role_permissions, user_sessions
- **Danh mục**: products, locations, promotions
- **Thiết bị**: machines, slots, device_events, device_telemetry
- **Kho**: inventory_batches, bottles, inventory_logs
- **Đơn và thanh toán**: orders, order_status_history, payments, payment_webhook_events, refunds
- **Xịt**: dispense_commands
- **Vận hành**: alerts, maintenance_tickets, maintenance_checklist_items, notifications
- **Hệ thống**: audit_logs, platform_settings

(Tên bảng chính xác xem `src/infrastructure/models/`.)

## 5. Cấu hình (`.env`)

| Biến | Ý nghĩa |
|---|---|
| `DATABASE_URI` | Chuỗi kết nối MySQL (hoặc `sqlite:///scentstation.db` để chạy thử) |
| `SECRET_KEY` | Ký JWT |
| `DEVICE_MASTER_KEY` | Sinh secret thiết bị và ký lệnh |
| `PAYMENT_WEBHOOK_SECRET` | Ký/kiểm tra webhook |
| `SEED_SUPER_ADMIN_EMAIL/PASSWORD` | Tài khoản đầu tiên |
| `MOCK_PAYMENT_ENABLED` | Bật `/dev/mock-payment` (**tắt khi triển khai thật**) |
| `ORDER_TTL_MINUTES`, `COMMAND_TTL_SECONDS`, `HEARTBEAT_ONLINE_SECONDS` | Thời gian chờ |


