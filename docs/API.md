# API Reference – ScentStation v1

Base URL: `http://localhost:9999/api/v1`. Swagger tự sinh: `http://localhost:9999/docs` (schema chính xác nhất, luôn đúng với code).

## 1. Quy ước chung

| Mục | Quy ước |
|---|---|
| Xác thực người dùng | Header `Authorization: Bearer <JWT>` (lấy từ `/auth/login`). Token gắn với một session trong DB nên **thu hồi được** (logout, khóa tài khoản). |
| Xác thực thiết bị | Header `X-Device-Serial` + `X-Device-Secret` (secret hiện **một lần** khi đăng ký máy). |
| Cô lập tenant | `tenant_id` luôn lấy từ JWT, không bao giờ từ body (trừ Super Admin khi tạo user). Dữ liệu brand khác → **404**. |
| Định dạng lỗi | `{"error_code": "...", "message": "..."}` kèm HTTP status. |
| Mã lỗi chung | 400/422 dữ liệu sai · 401 chưa đăng nhập/sai chữ ký · 403 thiếu quyền hoặc thiếu step-up · 404 không thấy · 409 xung đột · 422 vi phạm luật nghiệp vụ / chuyển trạng thái không hợp lệ |
| Phân trang/lọc | `limit` (mặc định 100, tối đa theo `MAX_PAGE_SIZE`), các `?status=`, `?machine_id=` ghi ở từng endpoint |

**Step-up**: hành động nhạy cảm (hoàn tiền, test spray) cần gọi `POST /auth/step-up` (nhập lại mật khẩu) trước; hiệu lực gắn với session.

## 2. Auth

| Method | Path | Quyền | Mô tả |
|---|---|---|---|
| POST | `/auth/login` | công khai | `{email, password}` → `{token, user, roles, permissions}`. Sai 5 lần liên tiếp → khóa tài khoản. |
| POST | `/auth/logout` | đăng nhập | Thu hồi session hiện tại. |
| GET | `/auth/me` | đăng nhập | Thông tin người dùng, role, permission. FE dùng để ẩn/hiện menu. |
| POST | `/auth/step-up` | đăng nhập | `{password}` → bật cờ step-up cho session. |

## 3. Brand (tenant) và người dùng

| Method | Path | Quyền | Mô tả |
|---|---|---|---|
| POST | `/tenants` | `TENANT_MANAGE` (Super Admin) | `{name, code, description?, contact_email?, contact_phone?, logo_url?}` |
| GET | `/tenants` | `TENANT_MANAGE` | Danh sách brand. |
| GET | `/tenants/{id}` | `TENANT_MANAGE` | Chi tiết. |
| PATCH | `/tenants/{id}/status` | `TENANT_MANAGE` | `{status: ACTIVE|SUSPENDED|INACTIVE}`. Suspend → người dùng của brand không đăng nhập được. |
| POST | `/users` | `USER_MANAGE` | `{email, password(≥8), full_name, role_codes[], tenant_id?, phone?}`. Brand Admin chỉ tạo trong brand mình. |
| GET | `/users` | `USER_MANAGE` | Người dùng trong phạm vi tenant. |
| PATCH | `/users/{id}/status` | `USER_MANAGE` | `{status: ACTIVE|INACTIVE|LOCKED}`. Vô hiệu hóa → hủy session đang mở. |

## 4. Danh mục: sản phẩm, địa điểm

| Method | Path | Quyền | Mô tả |
|---|---|---|---|
| POST | `/products` | `PRODUCT_MANAGE` | `{sku, name, default_price_per_spray, description?, image_url?, top_notes?, middle_notes?, base_notes?, usage_instructions?, product_qr_url?, is_available?}` |
| GET | `/products` | `PRODUCT_VIEW` | Danh sách sản phẩm của brand. |
| GET | `/products/{id}` | `PRODUCT_VIEW` | Chi tiết (brand khác → 404). |
| PUT | `/products/{id}` | `PRODUCT_MANAGE` | Cập nhật (đổi giá được ghi audit log). |
| POST | `/locations` | `LOCATION_MANAGE` | `{name, address?, city?}` |
| GET | `/locations` | `MACHINE_VIEW` | Danh sách địa điểm. |

## 5. Máy và slot

| Method | Path | Quyền | Mô tả |
|---|---|---|---|
| POST | `/machines` | `MACHINE_MANAGE` | `{serial_number, name?, location_id?, slot_count=4}` → trả `device_secret` **một lần duy nhất**. |
| GET | `/machines` | `MACHINE_VIEW` | Danh sách máy + trạng thái kết nối (ONLINE/UNSTABLE/OFFLINE tính từ heartbeat cuối). |
| GET | `/machines/{id}` | `MACHINE_VIEW` | Chi tiết máy, các slot, chai đang lắp, tồn ước tính. |
| PATCH | `/machines/{id}/mode` | `MACHINE_CONTROL` / `MACHINE_MAINTENANCE` | `{mode: NORMAL|MAINTENANCE|DISABLED, post_test_passed?}`. Từ MAINTENANCE về NORMAL bắt buộc `post_test_passed=true`. |
| POST | `/machines/{id}/revoke` | `MACHINE_MANAGE` | Thu hồi định danh thiết bị (máy bị từ chối ngay lần gọi sau). |
| POST | `/machines/{id}/test-spray` | `DEVICE_TEST_SPRAY` + **step-up** | `{slot_number}` → tạo lệnh TEST, ghi riêng, không trừ tồn bán hàng. |
| PUT | `/slots/{slot_id}` | `SLOT_CONFIGURE` | `{product_id?, price?, dosage_ms?, ml_per_spray?, low_stock_threshold?, enabled?}` |

## 6. Kho (inventory)

| Method | Path | Quyền | Mô tả |
|---|---|---|---|
| POST | `/inventory/batches` | `INVENTORY_MANAGE` | `{product_id, batch_number, quantity, received_date, expiration_date?}` |
| GET | `/inventory/batches` | `INVENTORY_VIEW` | Danh sách lô. |
| POST | `/inventory/bottles` | `INVENTORY_MANAGE` | `{batch_id, unique_code, capacity_ml, initial_weight_g?}` |
| GET | `/inventory/bottles` | `INVENTORY_VIEW` | Lọc theo trạng thái (AVAILABLE, INSTALLED, NEARLY_EMPTY, EMPTY, DAMAGED, EXPIRED). |
| POST | `/inventory/slots/{slot_id}/install-bottle` | `INVENTORY_MANAGE` | `{bottle_id, weight_before?, weight_after?}`. Kiểm tra đúng nước hoa cho slot; một slot chỉ một chai active; ghi lịch sử INSTALL/REPLACE. |

## 7. Kiosk (khách hàng) – xác thực bằng thiết bị

| Method | Path | Mô tả |
|---|---|---|
| GET | `/kiosk/catalog` | `{orderable, reason, items[]}`: `orderable=false` kèm `reason` khi máy chưa an toàn để bán; `items` là các slot đang bán được. |
| POST | `/kiosk/orders` | `{slot_number}` → tạo đơn, khóa giá/sản phẩm, trả `{order, payment, message}`: `order` (có `order_code`, `expires_at`), `payment` (có `payment_reference`, `qr_content`), `message` hiển thị cho khách. Từ chối nếu máy/slot không an toàn để xịt. |
| GET | `/kiosk/orders/{order_code}` | Poll trạng thái: `{order, payment, ..., message}`. `message` là câu hướng dẫn cho khách theo trạng thái (kể cả khi đã trả tiền nhưng xịt lỗi). |

## 8. Thiết bị (kiosk/simulator) – xác thực bằng thiết bị

| Method | Path | Mô tả |
|---|---|---|
| POST | `/device/heartbeat` | `{firmware_version?, telemetry[], events[]}`. Mỗi phần tử có `event_uid` → gửi lại cùng uid không tạo bản ghi trùng (đồng bộ sau khi mất mạng). |
| GET | `/device/commands` | Lấy lệnh xịt đang chờ (đã ký HMAC, có hạn dùng). |
| POST | `/device/commands/{command_id}/ack` | Xác nhận đã nhận lệnh (bắt buộc trước khi xịt). |
| POST | `/device/commands/{command_id}/result` | `{status: EXECUTED|FAILED|REJECTED, failure_code?, sensor_data?}`. Chỉ `EXECUTED` mới đưa đơn sang DISPENSED và trừ tồn. |

## 9. Đơn hàng và thanh toán

| Method | Path | Quyền | Mô tả |
|---|---|---|---|
| GET | `/orders` | `ORDER_VIEW` | `?status=&machine_id=&review_queue=true&limit=`. `review_queue=true` = đơn đã trả tiền nhưng chưa xác nhận xịt (DISPENSE_FAILED, UNCERTAIN, MANUAL_REVIEW). |
| GET | `/orders/{id}` | `ORDER_VIEW` | Chi tiết + lịch sử trạng thái + thanh toán + lệnh. |
| POST | `/orders/{id}/refund` | `ORDER_REFUND` + **step-up** | `{reason}` → REFUNDED. Ghi audit log. |
| POST | `/webhooks/payment` | chữ ký HMAC (`X-Signature`) | Webhook của nhà cung cấp thanh toán. Kiểm tra chữ ký, `payment_reference`, số tiền, tiền tệ; trùng `event_id` → `duplicate_ignored`. |
| POST | `/dev/mock-payment` | chỉ khi `MOCK_PAYMENT_ENABLED=true` | `{payment_reference, status=SUCCESS|FAILED|CANCELLED, event_id?, amount?, currency=VND}` giả lập nhà cung cấp. |

## 10. Cảnh báo, audit, hệ thống

| Method | Path | Quyền | Mô tả |
|---|---|---|---|
| GET | `/alerts` | `ALERT_VIEW` | `?status=&limit=` |
| POST | `/alerts/{id}/acknowledge` | `ALERT_MANAGE` | Ghi người nhận và thời điểm. |
| POST | `/alerts/{id}/resolve` | `ALERT_MANAGE` | `{note?}` |
| GET | `/audit-logs` | `AUDIT_VIEW` / `PLATFORM_AUDIT` | `?action=&order_id=&limit=`. Chỉ đọc. `order_id` cho phép lần theo chuỗi đơn → thanh toán → lệnh → tồn kho. |
| POST | `/system/jobs/run` | `JOBS_RUN` | Chạy job nền thủ công: hết hạn đơn chưa trả tiền, lệnh quá hạn → UNCERTAIN, làm mới trạng thái kết nối máy. |
| GET | `/health` | công khai | Kiểm tra sống. |

## 11. Ví dụ luồng mua hàng (curl)

```bash
# 1. Kiosk xem danh sách
curl -H "X-Device-Serial: KIOSK-001" -H "X-Device-Secret: $SECRET" localhost:9999/api/v1/kiosk/catalog
# 2. Tạo đơn cho slot 1
curl -X POST -H "Content-Type: application/json" -H "X-Device-Serial: KIOSK-001" -H "X-Device-Secret: $SECRET" \
     -d '{"slot_number":1}' localhost:9999/api/v1/kiosk/orders
# 3. Giả lập thanh toán
curl -X POST -H "Content-Type: application/json" \
     -d '{"payment_reference":"<payment_reference>"}' localhost:9999/api/v1/dev/mock-payment
# 4. Simulator nhận lệnh, xịt, báo kết quả; kiosk poll:
curl -H "X-Device-Serial: KIOSK-001" -H "X-Device-Secret: $SECRET" localhost:9999/api/v1/kiosk/orders/<order_code>
```
