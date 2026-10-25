# TP3 – P5: Alert System (Hệ thống cảnh báo)

## 1. Mục tiêu
Phát hiện, phân loại, lưu trạng thái và quản lý cảnh báo vận hành kiosk ScentStation theo từng tenant.

## 2. Công việc (Tasks)
- Nhận dữ liệu máy và slot đã được xác thực từ IoT Gateway/MQTT.
- Phát hiện mất kết nối, mức nước hoa thấp/hết, cửa mở, nghi ngờ rò rỉ, lỗi cảm biến, cơ cấu xịt và lỗi xịt.
- Phân loại mức độ cảnh báo; chống tạo cảnh báo trùng khi lỗi chưa được xử lý.
- Hỗ trợ xác nhận, xử lý, mở lại cảnh báo; ghi nhận người thao tác.
- Cung cấp danh sách cảnh báo theo tenant cho giao diện quản trị.

## 3. Đầu ra (Deliverables)
- Logic phát hiện và phân loại cảnh báo.
- Bộ quản lý trạng thái cảnh báo và lịch sử lần xuất hiện.
- Mô hình dữ liệu cảnh báo và kịch bản kiểm thử.

## 4. Quy tắc xử lý
| Mã | Điều kiện ví dụ | Mức độ |
|---|---|---|
| OFFLINE | Không nhận heartbeat quá ngưỡng do P3 xác định | Critical |
| LOW_STOCK | Lượng còn lại dưới ngưỡng cấu hình | Warning |
| EMPTY_SLOT | Slot hết nước hoa | Critical |
| DOOR_OPEN | Cửa mở | Warning |
| LEAK_SUSPECTED | Thiết bị phát hiện dấu hiệu rò rỉ | Critical |
| SENSOR_FAILURE | Cảm biến lỗi | Critical |
| ACTUATOR_FAILURE | Cơ cấu xịt lỗi | Critical |
| DISPENSE_FAILURE | Xịt thất bại | Warning |

**Lưu ý:** Ngưỡng 15% trong code chỉ là giá trị minh họa, phải cấu hình theo máy/slot thực tế. Cảnh báo không tự cấp quyền xịt hay tự gửi lệnh điều khiển. Cơ chế an toàn vật lý vẫn thuộc TP2.

## 5. Luồng xử lý
Thiết bị TP2 → MQTT TP3/P2 → Gateway TP3/P1 → Monitoring TP3/P3 → Alert Engine TP3/P5 → Web Portal TP5.

Khi phát hiện sự cố: kiểm tra dữ liệu → tìm cảnh báo chưa giải quyết cùng tenant/máy/slot/loại → tạo mới hoặc tăng số lần xuất hiện → hiển thị và thông báo → người có quyền xác nhận/giải quyết.

## 6. Cách chạy bản mẫu
Yêu cầu Python 3.10 trở lên. Mở terminal tại thư mục này:

```bash
python alert_system.py
python -m unittest -v
```

Đây là **prototype logic độc lập**, chưa phải backend production: dữ liệu nằm trong bộ nhớ, chưa có MQTT Broker thật, cơ sở dữ liệu, API đăng nhập, kênh thông báo ngoài, cơ chế escalation hoặc tự tạo maintenance ticket. Các phần này cần tích hợp với TP1, TP3/P1–P4 và TP5.

## 7. Kiểm thử và nghiệm thu
- Sinh đúng cảnh báo cho dữ liệu bất thường.
- Cảnh báo cùng lỗi chưa giải quyết không bị tạo bản ghi trùng.
- Có trạng thái OPEN, ACKNOWLEDGED, RESOLVED.
- Danh sách cảnh báo của tenant A không hiển thị cho tenant B.
- Kết nối MQTT và thông báo thực tế cần kiểm thử trong P6 – Integration Testing.

## 8. Liên kết các TP khác
- **TP1:** tenant, phân quyền, lưu trữ, audit log.
- **TP2:** tín hiệu cảm biến, cửa, cơ cấu xịt và lỗi firmware.
- **TP3/P1–P4:** gateway, MQTT, giám sát, điều khiển từ xa.
- **TP4:** hiển thị hướng dẫn khi kiosk không sẵn sàng.
- **TP5:** hiển thị cảnh báo, phân công bảo trì, thông báo.
- **TP6:** kiểm thử tích hợp đầu cuối, bảo mật, triển khai.
