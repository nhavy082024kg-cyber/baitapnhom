# TP3 – P5: Alert System (Hệ thống cảnh báo)

> **Dự án:** ScentStation – Multi-Brand IoT Perfume Experience and Management Platform  
> **Cơ sở tài liệu:** `TP3_P5_Alert_System.zip` gồm `alert_system.py`, `test_alert_system.py`, `README.md`.  
> **Trạng thái:** Đã có bản mẫu xử lý cảnh báo độc lập bằng Python; **chưa tích hợp MQTT, CSDL và Web Portal thực tế**.

## 1. Mục tiêu (Objective)

Xây dựng bộ xử lý cảnh báo cho kiosk ScentStation, có khả năng nhận dữ liệu trạng thái thiết bị đã được xác thực, phát hiện lỗi, phân loại mức độ, hạn chế cảnh báo trùng, quản lý trạng thái và cung cấp danh sách cảnh báo theo tenant.

## 2. Phạm vi công việc (Scope & Tasks)

1. **Nhận dữ liệu (Telemetry Input):** Tiếp nhận thông tin máy, slot và tín hiệu lỗi từ Gateway/Monitoring sau khi nguồn gửi được xác thực.
2. **Phát hiện bất thường (Detection):** Nhận diện mất kết nối, mức nước hoa thấp/hết, cửa mở, rò rỉ nghi ngờ, lỗi cảm biến, lỗi cơ cấu xịt và lỗi xịt.
3. **Phân loại (Severity Classification):** Gán mức `warning` hoặc `critical` theo mã lỗi.
4. **Chống trùng (Deduplication):** Với cảnh báo chưa giải quyết cùng tenant, máy, loại lỗi và slot, tăng số lần xuất hiện thay vì tạo thêm bản ghi.
5. **Quản lý vòng đời (Alert Lifecycle):** Hỗ trợ `OPEN`, `ACKNOWLEDGED`, `RESOLVED`, lưu người xác nhận/người giải quyết.
6. **Truy vấn theo tenant (Tenant-scoped Listing):** Trả về danh sách cảnh báo theo `tenant_id`.

## 3. Các file đã có trong bộ code

| File | Vai trò | Trạng thái |
|---|---|---|
| `alert_system.py` | Khai báo `Alert`, `AlertEngine`; phát hiện, phân loại, chống trùng và cập nhật cảnh báo | Đã có |
| `test_alert_system.py` | Kiểm thử chống trùng/giải quyết, lọc theo tenant, lỗi cảm biến và slot hết | Đã có |
| `README.md` | Mô tả phạm vi, quy tắc, cách chạy, tích hợp và giới hạn | Đã có |

### Các thành phần chính trong code

- `Alert`: dữ liệu cảnh báo gồm `tenant_id`, `machine_id`, `code`, `slot_id`, `severity`, `status`, `occurrences`, `first_seen`, `last_seen`, `acknowledged_by`, `resolved_by`.
- `AlertEngine.process_telemetry(payload)`: kiểm tra dữ liệu đầu vào và phát hiện cảnh báo.
- `AlertEngine.raise_alert(...)`: tạo cảnh báo hoặc tăng số lần xuất hiện nếu cảnh báo tương ứng chưa được giải quyết.
- `AlertEngine.update_status(...)`: đổi trạng thái, yêu cầu tên người thao tác.
- `AlertEngine.list_alerts(tenant_id)`: lọc danh sách theo tenant.

## 4. Bảng quy tắc cảnh báo (Alert Rules)

| Mã cảnh báo | Điều kiện trong code | Mức độ |
|---|---|---|
| `OFFLINE` | Dữ liệu có `online = false` | Critical |
| `LOW_STOCK` | `0 < remaining_percent < 15` (ngưỡng mặc định) | Warning |
| `EMPTY_SLOT` | `remaining_percent = 0` | Critical |
| `DOOR_OPEN` | `door_open = true` | Warning |
| `LEAK_SUSPECTED` | `leak_suspected = true` | Critical |
| `SENSOR_FAILURE` | `sensor_error = true` | Critical |
| `ACTUATOR_FAILURE` | `actuator_error = true` | Critical |
| `DISPENSE_FAILURE` | `dispense_failed = true` | Warning |

**Ghi chú:** Ngưỡng `15%` là mặc định minh họa trong `AlertEngine(low_stock_threshold=15)`, có thể thay đổi. Việc xác định timeout heartbeat và chuyển thành `online=false` phải do thành phần bên ngoài thực hiện; P5 hiện chưa tự theo dõi thời gian mất kết nối.

## 5. Luồng xử lý và điểm tích hợp

```text
TP2 – Thiết bị / Prototype (trạng thái, cảm biến, lỗi)
                   |
                   v
TP3/P2 – MQTT Communication [chưa tích hợp]
                   |
                   v
TP3/P1 – IoT Gateway [chưa tích hợp]
                   |
                   v
TP3/P3 – Machine Monitoring [chưa tích hợp]
                   |
                   v
TP3/P5 – AlertEngine (đã có bản mẫu Python)
                   |
                   v
TP5 – Web Portal / Notifications [chưa tích hợp]
```

**Xử lý nội bộ P5:** Nhận `payload` → kiểm tra định danh tenant/máy và dữ liệu slot → xác định mã lỗi → tìm khóa `(tenant_id, machine_id, code, slot_id)` → tạo mới hoặc cập nhật `occurrences`/`last_seen` → cho phép xác nhận hoặc giải quyết → liệt kê theo tenant.

## 6. Dữ liệu đầu vào mẫu

```json
{
  "tenant_id": "brand_a",
  "machine_id": "kiosk_01",
  "online": true,
  "door_open": false,
  "slots": [
    {"slot_id": 1, "remaining_percent": 10},
    {"slot_id": 2, "remaining_percent": 0},
    {"slot_id": 3, "sensor_error": true},
    {"slot_id": 4, "remaining_percent": 75}
  ]
}
```

**Kết quả dự kiến:** Tạo `LOW_STOCK` cho slot 1, `EMPTY_SLOT` cho slot 2 và `SENSOR_FAILURE` cho slot 3. Slot 4 không phát sinh cảnh báo. Ví dụ này có sẵn trong chương trình `alert_system.py`.

## 7. Hướng dẫn chạy và sử dụng bản mẫu

Yêu cầu **Python 3.10 trở lên**. Giải nén `TP3_P5_Alert_System.zip`, mở Terminal trong thư mục chứa các file và chạy:

```bash
python alert_system.py
```

Chương trình in danh sách cảnh báo mẫu dưới dạng JSON. Chạy bộ kiểm thử:

```bash
python -m unittest -v
```

| Bước | Thao tác | Kết quả mong đợi |
|---|---|---|
| 1 | Mở thư mục code trong VS Code | Thấy đủ ba file Python/Markdown |
| 2 | Chạy `python alert_system.py` | In cảnh báo mẫu theo `brand_a` |
| 3 | Xem mã và mức độ | Có LOW_STOCK, EMPTY_SLOT, SENSOR_FAILURE |
| 4 | Chạy `python -m unittest -v` | Các bài test báo `ok` |
| 5 | Gọi `process_telemetry()` nhiều lần với cùng lỗi | `occurrences` tăng, không tạo thêm cảnh báo chưa giải quyết |
| 6 | Gọi `update_status()` với actor hợp lệ | Cập nhật trạng thái cảnh báo |
| 7 | Gọi `list_alerts()` với tenant khác | Không trả về cảnh báo của tenant đầu tiên |

## 8. Kiểm thử (Testing)

| Test trong `test_alert_system.py` | Nội dung | Kết quả chạy lại |
|---|---|---|
| `test_deduplicate_and_resolve` | Chống trùng, tăng số lần xuất hiện, chuyển `RESOLVED` | PASS |
| `test_tenant_isolation` | Lọc danh sách cảnh báo theo tenant | PASS |
| `test_sensor_and_empty` | Tạo cảnh báo hết slot và lỗi cảm biến | PASS |

**Kết quả kiểm tra tại thời điểm lập tài liệu:** `3 tests`, `OK` khi chạy `python -m unittest -v`. Đây là kiểm thử logic độc lập, **không phải kiểm thử tích hợp MQTT hoặc kiểm thử bảo mật hệ thống**.

## 9. Đầu ra (Deliverables)

1. **Hệ thống cảnh báo (Alert System):** Bản mẫu logic Python phát hiện, phân loại và quản lý trạng thái cảnh báo.
2. **Danh sách cảnh báo và lịch sử xử lý:** Có danh sách lọc theo tenant, thời điểm xuất hiện, số lần xuất hiện và thông tin người xác nhận/giải quyết trong bộ nhớ. **Chưa có lưu trữ lịch sử bền vững hoặc nhật ký mọi lần thay đổi trạng thái.**

## 10. Tiêu chí nghiệm thu (Acceptance Criteria)

- [x] Phát hiện các tình huống lỗi theo quy tắc hiện có.
- [x] Hạn chế bản ghi trùng đối với cùng lỗi chưa giải quyết.
- [x] Hỗ trợ `OPEN`, `ACKNOWLEDGED`, `RESOLVED`.
- [x] Có phương thức liệt kê cảnh báo theo tenant.
- [x] Ba bài kiểm thử Python hiện có chạy thành công.
- [ ] Xác thực danh tính nguồn dữ liệu và phân quyền người dùng bằng TP1.
- [ ] Nhận dữ liệu thật từ MQTT/Gateway/Monitoring.
- [ ] Lưu cảnh báo và lịch sử thay đổi vào CSDL.
- [ ] Hiển thị cảnh báo trên Web Portal và gửi thông báo thực tế.
- [ ] Kiểm thử tích hợp và bảo mật đầu cuối.

## 11. Liên kết với các Task Package

| TP / Phần | Dữ liệu hoặc trách nhiệm liên quan |
|---|---|
| **TP1** | Cung cấp tenant, định danh máy, xác thực, phân quyền, PostgreSQL/RLS và audit |
| **TP2** | Cung cấp trạng thái slot, tín hiệu cảm biến, lỗi firmware và kết quả xịt từ prototype |
| **TP3/P1 – IoT Gateway** | Chuyển tiếp sự kiện thiết bị tới Backend |
| **TP3/P2 – MQTT Communication** | Truyền thông điệp thiết bị qua MQTT |
| **TP3/P3 – Machine Monitoring** | Theo dõi heartbeat/telemetry, xác định offline |
| **TP3/P4 – Remote Commands** | Cung cấp kết quả hoặc lỗi thực thi lệnh để tạo cảnh báo |
| **TP4** | Hiển thị trạng thái không sẵn sàng trên kiosk khi phù hợp |
| **TP5** | Hiển thị danh sách cảnh báo, hỗ trợ bảo trì và thông báo |
| **TP6** | Kiểm thử tích hợp, bảo mật, độ tin cậy và triển khai |

## 12. Giới hạn hiện tại và lưu ý bàn giao

- Bộ xử lý **chạy độc lập** và lưu cảnh báo trong `dict` Python; tắt chương trình là mất dữ liệu.
- `tenant_id` trong payload phải được xác thực ở Gateway/Backend; chỉ lọc theo tenant trong code **chưa thay thế được** xác thực, RBAC và RLS.
- Cảnh báo đã `RESOLVED` có thể được tạo lại khi lỗi tái diễn, nhưng khóa cũ bị thay thế trong bộ nhớ; chưa lưu lịch sử đầy đủ các lần tái phát.
- `update_status()` yêu cầu tên người thao tác nhưng chưa tự kiểm tra quyền của người đó.
- Không có MQTT Broker, REST API, Web Portal, kênh thông báo, escalation hay maintenance ticket trong ZIP hiện tại.
- Cơ chế an toàn thiết bị và quyền cho phép xịt vẫn thuộc các phần tương ứng của TP2 và Backend, **không do Alert System quyết định**.

**Kết luận:** TP3/P5 đã có **prototype Alert Engine** để thử nghiệm và làm nền tích hợp. Để trở thành Alert System hoàn chỉnh của ScentStation, cần nối dữ liệu từ TP3/P1–P3, kết quả lệnh TP3/P4, quyền và CSDL TP1, giao diện TP5, sau đó kiểm thử tại TP3/P6 và TP6.
