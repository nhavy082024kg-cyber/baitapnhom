# Phân quyền (RBAC) và đặc tả use case

Không thêm quan hệ include/extend theo yêu cầu của nhóm: mỗi use case là một chức năng độc lập, gắn với một actor.
Nguồn quyền: `DEFAULT_ROLE_PERMISSIONS` trong `src/domain/constants.py`. 6 role hệ thống, 20 permission.

## 1. Ma trận quyền theo role

✔ = có quyền mặc định. Step-up = phải nhập lại mật khẩu trước khi làm.

| Permission | Super Admin | Brand Admin | Ops Manager | Technician | Inventory | Viewer |
|---|:-:|:-:|:-:|:-:|:-:|:-:|
| TENANT_MANAGE | ✔ | | | | | |
| PLATFORM_AUDIT, JOBS_RUN | ✔ | | | | | |
| USER_MANAGE | ✔ | ✔ | | | | |
| PRODUCT_MANAGE | | ✔ | | | | |
| PRODUCT_VIEW | | ✔ | ✔ | | ✔ | ✔ |
| LOCATION_MANAGE | | ✔ | | | | |
| MACHINE_MANAGE | | ✔ | | | | |
| MACHINE_VIEW | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ |
| MACHINE_CONTROL | | ✔ | ✔ | | | |
| MACHINE_MAINTENANCE | | ✔ | | ✔ | | |
| SLOT_CONFIGURE | | ✔ | | | | |
| INVENTORY_MANAGE | | ✔ | | | ✔ | |
| INVENTORY_VIEW | | ✔ | ✔ | | ✔ | ✔ |
| ORDER_VIEW | | ✔ | ✔ | | | ✔ |
| ORDER_REFUND (step-up) | | | ✔ | | | |
| DEVICE_TEST_SPRAY (step-up) | | | | ✔ | | |
| ALERT_VIEW | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ |
| ALERT_MANAGE | | ✔ | ✔ | ✔ | | |
| AUDIT_VIEW | ✔ | ✔ | | | | |

Super Admin quản trị nền tảng, **không** xem dữ liệu bán hàng chi tiết của brand (đúng yêu cầu cô lập dữ liệu).

## 2. Danh sách use case theo actor và trạng thái cài đặt

Trạng thái: **BE** = đã có API + test · **Bảng** = đã có bảng, chưa có API · **—** = chưa làm.

### 2.1 Platform Super Administrator
| ID | Use case | Trạng thái | API |
|---|---|---|---|
| UC-SA-01 | Tạo/sửa/ngừng brand (tenant) | BE | `/tenants` |
| UC-SA-02 | Tạo tài khoản Brand Admin | BE | `POST /users` |
| UC-SA-03 | Giám sát toàn bộ máy | BE | `/machines` |
| UC-SA-04 | Xem audit log nền tảng | BE | `/audit-logs` |
| UC-SA-05 | Chạy job nền | BE | `/system/jobs/run` |
| UC-SA-06 | Cấu hình nền tảng (provider, template) | Bảng | — |
| UC-SA-07 | Thống kê toàn nền tảng | — | — |

### 2.2 Brand Administrator
| ID | Use case | Trạng thái | API |
|---|---|---|---|
| UC-BA-01 | Quản lý tài khoản nhân sự và role | BE | `/users` |
| UC-BA-02 | Quản lý sản phẩm nước hoa (giá/xịt, notes, ảnh) | BE | `/products` |
| UC-BA-03 | Quản lý địa điểm, đăng ký máy | BE | `/locations`, `/machines` |
| UC-BA-04 | Cấu hình slot: sản phẩm, giá, liều xịt, ngưỡng | BE | `PUT /slots/{id}` |
| UC-BA-05 | Khuyến mãi / dùng thử miễn phí | Bảng | — |
| UC-BA-06 | Xuất báo cáo theo nước hoa, máy, địa điểm | — | — |

### 2.3 Operations Manager
| ID | Use case | Trạng thái | API |
|---|---|---|---|
| UC-OM-01 | Giám sát máy, slot, tồn ước tính | BE | `/machines` |
| UC-OM-02 | Bật/tắt máy | BE | `PATCH /machines/{id}/mode` |
| UC-OM-03 | Hàng đợi đơn đã trả tiền chưa xịt | BE | `GET /orders?review_queue=true` |
| UC-OM-04 | Hoàn tiền (step-up) | BE | `POST /orders/{id}/refund` |
| UC-OM-05 | Nhận, nhận việc, đóng cảnh báo | BE | `/alerts` |
| UC-OM-06 | Tạo/giao ticket bảo trì | Bảng | — |
| UC-OM-07 | Dashboard vận hành | — | — |

### 2.4 Technician
| ID | Use case | Trạng thái | API |
|---|---|---|---|
| UC-TE-01 | Xem máy và cảnh báo được giao | BE | `/machines`, `/alerts` |
| UC-TE-02 | Đưa máy vào chế độ bảo trì | BE | `PATCH /machines/{id}/mode` |
| UC-TE-03 | Test spray (step-up, ghi riêng) | BE | `POST /machines/{id}/test-spray` |
| UC-TE-04 | Checklist và đóng ticket bảo trì | Bảng | — |
| UC-TE-05 | Test sau bảo trì rồi mới trả máy | BE | `mode` + `post_test_passed` |

### 2.5 Inventory Staff
| ID | Use case | Trạng thái | API |
|---|---|---|---|
| UC-IS-01 | Nhập lô nước hoa | BE | `/inventory/batches` |
| UC-IS-02 | Đăng ký chai/cartridge | BE | `/inventory/bottles` |
| UC-IS-03 | Lắp/thay chai vào slot, ghi cân nặng | BE | `install-bottle` |
| UC-IS-04 | Điều chỉnh tồn kèm lý do | Bảng | — |
| UC-IS-05 | Báo cáo tồn kho | — | — |

### 2.6 Khách hàng / Kiosk
| ID | Use case | Trạng thái | API |
|---|---|---|---|
| UC-CU-01 | Xem danh sách và thông tin nước hoa | BE | `/kiosk/catalog` |
| UC-CU-02 | Chọn nước hoa, xác nhận giá, tạo đơn | BE | `POST /kiosk/orders` |
| UC-CU-03 | Quét QR, xem trạng thái thanh toán | BE | `GET /kiosk/orders/{code}` |
| UC-CU-04 | Nhận một lần xịt, xem trạng thái xịt | BE | như trên |
| UC-CU-05 | Hướng dẫn xử lý khi trả tiền nhưng xịt lỗi | BE | trường `message` |
| UC-CU-06 | Quét QR sản phẩm xem khuyến mãi | — | `product_qr_url` đã lưu |

### 2.7 Thiết bị (actor hệ thống ngoài)
| ID | Use case | Trạng thái | API |
|---|---|---|---|
| UC-DV-01 | Gửi heartbeat + telemetry + sự kiện | BE | `/device/heartbeat` |
| UC-DV-02 | Nhận, ack, thực thi, báo kết quả lệnh | BE | `/device/commands*` |

## 3. Đặc tả mẫu chi tiết (dùng làm mẫu cho các use case còn lại)

### UC-CU-02 Tạo đơn từ kiosk
- **Actor**: Khách hàng (qua kiosk đã xác thực thiết bị).
- **Tiền điều kiện**: máy ONLINE, NORMAL, cửa đóng; slot có sản phẩm, giá và đủ nước hoa.
- **Luồng chính**: (1) chọn slot → (2) hệ thống kiểm tra policy → (3) tạo đơn, **khóa** sản phẩm/giá/tiền tệ/hạn → (4) sinh `payment_reference` + QR → (5) trả về kiosk, đơn AWAITING_PAYMENT.
- **Luồng thay thế**: slot hết/thấp → từ chối "không đủ nước hoa"; máy bảo trì/ offline/ cửa mở → từ chối, kiosk hiển thị tạm ngưng.
- **Hậu điều kiện**: có một đơn và một bản ghi thanh toán WAITING; audit log ghi nhận.
- **Quy tắc**: giá không đổi sau khi tạo; hạn thanh toán `ORDER_TTL_MINUTES`.

### UC-OM-04 Hoàn tiền
- **Actor**: Operations Manager.
- **Tiền điều kiện**: đơn ở DISPENSE_FAILED, UNCERTAIN hoặc MANUAL_REVIEW; đã step-up.
- **Luồng chính**: (1) mở hàng đợi review → (2) chọn đơn, xem chuỗi chứng cứ (thanh toán, lệnh, kết quả thiết bị) → (3) nhập lý do → (4) hệ thống tạo refund, đơn REFUNDED, ghi audit.
- **Ngoại lệ**: chưa step-up → 403; đơn đã DISPENSED → 422 (không hoàn).
- **Hậu điều kiện**: không sinh thêm lệnh xịt nào.
