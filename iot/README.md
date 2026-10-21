# P1 – IoT Gateway (ScentStation)

Phần P1 chạy **độc lập hoàn toàn**: chỉ cần Python, Flask và pydantic. Không import gì từ Task 1, Task 3 hay các phần P2–P6.

## Phần P1 làm gì

Gateway là "cổng vào" của dữ liệu từ máy kiosk. Nó:

1. **Biết máy nào hợp lệ**: đăng ký máy cho đúng 1 brand (Dior, Gucci, Chanel, YSL, Hermès), cấp mật khẩu MQTT và khóa ký lệnh (hiển thị 1 lần, chỉ lưu bản băm).
2. **Trả lời broker**: `/iot/auth` (máy có đúng mật khẩu không), `/iot/acl` (máy được gửi/nhận topic nào).
3. **Kiểm tra mọi tin nhắn từ máy** (`Gateway.handle`) theo 8 bước, tin sai thì từ chối, không đổi dữ liệu, ghi `gateway_audit`.
4. **Lưu sự kiện không trùng** và ghi nhận máy còn sống (`last_seen_at`).
5. **Thu hồi / tạm dừng máy**. Trạng thái máy lưu bằng chữ thường (`active`, `disabled`, `revoked`), cùng quy ước với bảng `tenants` của nhóm (`active`, `suspended`).

## Cài đặt và chạy

```
cd iot_gateway_p1
pip install -r requirements.txt
python -m unittest discover -s tests -t . -v      # 30 test
python demo.py                                    # chạy thử kịch bản 5 brand
```

Chạy server:
```
set SS_GATEWAY_SECRET=bi-mat-broker      (Windows; macOS/Linux dùng export)
set SS_ADMIN_TOKEN=token-quan-tri
python -m gateway.app                    # http://127.0.0.1:5001
```
Quên đặt hai biến này thì các endpoint tương ứng trả 401 (không bao giờ mở cửa mặc định).

## Cấu trúc file

| File | Nội dung |
|---|---|
| `gateway/schema.sql` | 5 bảng: `tenants`, `machines`, `device_credentials`, `device_events`, `gateway_audit` |
| `gateway/config.py` | cấu hình từ biến môi trường |
| `gateway/db.py` | kết nối SQLite, tạo bảng |
| `gateway/topics.py` | quy ước topic `ss/<brand>/<serial>/<leaf>`, kiểm tra tên an toàn |
| `gateway/schemas.py` | cấu trúc JSON hợp lệ của telemetry, event, ack, result (pydantic) |
| `gateway/registry.py` | đăng ký máy, cấp/xoay bí mật, thu hồi, xác thực |
| `gateway/gateway.py` | **lớp `Gateway`**: `authenticate`, `authorize`, `handle` (trái tim P1), điểm nối `register_handler` |
| `gateway/api.py` | endpoint HTTP: hook broker + quản trị máy |
| `gateway/app.py` | tạo ứng dụng Flask |
| `tests/test_gateway.py` | 30 test |
| `demo.py` | kịch bản chạy thử |

## 8 bước kiểm tra trong `Gateway.handle`

| # | Kiểm tra | Mã từ chối |
|---|---|---|
| 1 | topic đúng dạng, leaf là loại máy được gửi | `BAD_TOPIC` |
| 2 | serial đã đăng ký | `UNKNOWN_DEVICE` |
| 3 | client id đã xác thực = serial trong topic | `IDENTITY_MISMATCH` |
| 4 | máy chưa bị thu hồi | `DEVICE_REVOKED` |
| 5 | mã brand trong topic = brand thật của máy | `TENANT_MISMATCH` |
| 6 | brand không bị khóa | `TENANT_SUSPENDED` |
| 7 | payload ≤ 16 KB | `PAYLOAD_TOO_LARGE` |
| 8 | JSON hợp lệ và đúng schema | `BAD_PAYLOAD` |

## Điểm nối cho các phần khác (không cần sửa code P1)

Các bạn P3, P4, P5 gắn xử lý của mình vào gateway bằng `register_handler`:

```python
from gateway.db import connect
from gateway.gateway import Gateway

db = connect("gateway.db")
gw = Gateway(db)

def xu_ly_telemetry(db, msg):          # P3
    # msg.machine["tenant_id"], msg.machine["id"], msg.body.mode, msg.body.slots ...
    ...

def xu_ly_result(db, msg):             # P4
    ...
    return [("ss/dior/SS-0001/result_ack", '{"command_id": "..."}')]   # (tuỳ chọn) tin cần phát lại cho máy

gw.register_handler("telemetry", xu_ly_telemetry)
gw.register_handler("result", xu_ly_result)
```

- Handler chỉ được gọi **sau khi** tin đã qua cả 8 kiểm tra.
- Với `event`: tin gửi trùng (event id đã có) **không** gọi handler lần nữa.
- Handler lỗi không làm gateway chết: phần handler ghi dở bị hủy, ghi `HANDLER_ERROR`, tin vẫn được coi là đã nhận.
- Danh sách `outbound` mà handler trả về nằm trong `Result.outbound`; cầu nối MQTT (P2) có nhiệm vụ phát chúng.

**P2 (MQTT)** chỉ cần: khi broker có tin → `gw.handle(topic, payload, client_id)`; hook xác thực của broker → `/iot/auth` và `/iot/acl` (hoặc `gw.authenticate`, `gw.authorize`).
**P4** lấy khóa ký lệnh bằng `registry.command_key(db, machine_id)`.
**P6** có thể thử luồng không cần broker bằng `POST /iot/ingest`.

## Giới hạn hiện tại (nói rõ để không hiểu nhầm)

- Chưa có broker MQTT nào được dùng thử; gateway nhận tin từ hàm `handle()` hoặc `/iot/ingest`.
- API quản trị dùng token tạm `X-Admin-Token`; khi ghép với đăng nhập/phân quyền của nhóm thì thay bằng JWT + RBAC.
- Bảng `tenants` ở đây là bản tối thiểu; khi ghép thì dùng bảng của phần quản trị brand và thêm khóa ngoại.
- CSDL là SQLite; chưa có bản PostgreSQL + RLS riêng cho P1.
