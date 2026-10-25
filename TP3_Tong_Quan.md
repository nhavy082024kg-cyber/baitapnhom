# TASK PACKAGE 3 — TỔNG QUAN
## IoT Gateway, MQTT Communication, Machine Monitoring, Remote Commands & Alert System

### 1. Mục tiêu
Xây dựng hệ thống kết nối và giám sát kiosk ScentStation từ xa, truyền dữ liệu thiết bị qua MQTT, tiếp nhận lệnh điều khiển hợp lệ và phát hiện các sự cố để cảnh báo người vận hành.

### Giải thích thuật ngữ
| Thuật ngữ | Giải thích cơ bản |
|---|---|
| IoT Gateway | Thành phần trung gian kết nối thiết bị với backend, tiếp nhận và chuyển tiếp dữ liệu |
| MQTT | Giao thức gửi/nhận thông điệp nhẹ cho thiết bị IoT |
| MQTT Broker | Máy chủ trung chuyển thông điệp MQTT |
| Topic | Kênh phân loại thông điệp MQTT |
| Heartbeat | Tín hiệu định kỳ cho biết thiết bị còn kết nối |
| Telemetry | Dữ liệu trạng thái và cảm biến gửi từ máy |
| Remote Commands | Lệnh điều khiển thiết bị từ xa |
| Alert System | Hệ thống phát hiện, ghi nhận và xử lý cảnh báo |
| Integration Testing | Kiểm thử các thành phần sau khi kết nối với nhau |

### 2. Phạm vi công việc (P1–P6)

#### P1 – IoT Gateway
- **Công việc (Tasks):** Thiết kế gateway kết nối kiosk với backend; tiếp nhận, kiểm tra và chuyển tiếp dữ liệu thiết bị.
- **Đầu ra (Deliverables):** Thiết kế IoT Gateway, chức năng xử lý và chuyển tiếp dữ liệu.
- **Tiêu chí hoàn thành:** Gateway tiếp nhận và định tuyến đúng thông điệp của thiết bị đã đăng ký.

#### P2 – MQTT Communication
- **Công việc (Tasks):** Thiết lập MQTT Broker, topic, kết nối bảo mật, gửi/nhận thông điệp và xử lý mất kết nối.
- **Đầu ra (Deliverables):** Mô hình giao tiếp MQTT, cấu hình Broker, kết quả truyền nhận dữ liệu.
- **Tiêu chí hoàn thành:** Thiết bị và gateway truyền nhận đúng topic, đúng định dạng và có xác thực.

#### P3 – Machine Monitoring
- **Công việc (Tasks):** Theo dõi heartbeat, online/offline, telemetry, cảm biến, trạng thái máy và các slot.
- **Đầu ra (Deliverables):** Chức năng giám sát máy, dữ liệu trạng thái và lịch sử hoạt động.
- **Tiêu chí hoàn thành:** Hệ thống cập nhật được trạng thái máy và phát hiện mất heartbeat.

#### P4 – Remote Commands
- **Công việc (Tasks):** Thiết kế gửi lệnh từ xa, kiểm tra quyền và tính hợp lệ, theo dõi phản hồi, timeout và chống xử lý lệnh trùng.
- **Đầu ra (Deliverables):** Chức năng điều khiển từ xa, quy trình xử lý lệnh, kết quả thực thi.
- **Tiêu chí hoàn thành:** Chỉ lệnh hợp lệ được chuyển đến đúng máy; kết quả và lỗi được ghi nhận.

#### P5 – Alert System
- **Công việc (Tasks):** Phát hiện máy offline, nước hoa thấp, lỗi cảm biến, lỗi xịt; phân loại, ghi nhận và quản lý trạng thái cảnh báo.
- **Đầu ra (Deliverables):** Hệ thống cảnh báo, danh sách cảnh báo và lịch sử xử lý.
- **Tiêu chí hoàn thành:** Cảnh báo được tạo đúng điều kiện, hạn chế trùng lặp và có thể theo dõi xử lý.

#### P6 – Integration Testing
- **Công việc (Tasks):** Tích hợp Gateway, MQTT, Monitoring, Commands và Alerts; kiểm thử luồng dữ liệu, xử lý lỗi, sửa và kiểm thử lại.
- **Đầu ra (Deliverables):** Bộ test case, kết quả kiểm thử tích hợp, biên bản nghiệm thu.
- **Tiêu chí hoàn thành:** Các thành phần hoạt động thông suốt với thiết bị mô phỏng hoặc prototype, có bằng chứng kiểm thử.

### 3. Thành phần chính
| Thành phần | Chức năng |
|---|---|
| IoT Gateway | Kết nối và chuyển tiếp dữ liệu giữa thiết bị và backend |
| MQTT Communication | Truyền nhận thông điệp bảo mật theo topic |
| Machine Monitoring | Theo dõi kết nối, cảm biến và tình trạng máy |
| Remote Commands | Gửi lệnh hợp lệ và ghi nhận phản hồi thực thi |
| Alert System | Phát hiện, phân loại và theo dõi cảnh báo |
| Integration Testing | Kiểm chứng hoạt động liên thông của TP3 |

### 4. Quy tắc quan trọng
- Chỉ thiết bị đã đăng ký và được cấp quyền mới được kết nối, gửi và nhận thông điệp.
- Mỗi lệnh phải có mã định danh, máy đích, thời hạn và cơ chế chống xử lý trùng.
- Không tự động xịt lại khi kết quả lệnh chưa rõ; lệnh xịt chỉ được phát sau xác nhận thanh toán từ backend và phải tuân thủ cơ chế an toàn TP2.
- Khi mất kết nối, không nhận đơn mới nếu không thể xác nhận điều kiện xịt an toàn.
- Sự kiện và cảnh báo phải gắn đúng máy, tenant và thời điểm; dữ liệu giữa các brand phải được cách ly.

### 5. Đầu ra dự kiến
- Thiết kế IoT Gateway và mô hình giao tiếp MQTT.
- Chức năng giám sát máy và lưu trạng thái thiết bị.
- Chức năng gửi lệnh từ xa, theo dõi phản hồi và kết quả.
- Hệ thống cảnh báo và lịch sử xử lý.
- Kết quả kiểm thử tích hợp TP3.

### 6. Tiêu chí nghiệm thu đề xuất
- Gateway và MQTT truyền nhận đúng thông điệp của thiết bị hợp lệ.
- Trạng thái online/offline, telemetry và các sự kiện được cập nhật và lưu vết.
- Lệnh từ xa được kiểm tra quyền, chống trùng và theo dõi đến kết quả cuối.
- Cảnh báo được kích hoạt đúng tình huống và không tạo trùng lặp quá mức.
- Có kết quả kiểm thử cả luồng bình thường lẫn lỗi, mất kết nối và khôi phục.

### 7. Liên kết với các Task Package khác
| Task Package | Liên kết với TP3 |
|---|---|
| **TP1 – System Analysis, Multi-Tenant, Database, Authentication & Brand Administration** | Cung cấp định danh tenant, máy, tài khoản, quyền truy cập, cấu trúc dữ liệu và nguyên tắc cách ly để TP3 xác thực thiết bị, lưu telemetry, lệnh và cảnh báo. |
| **TP2 – Kiosk Hardware Prototype, Embedded Firmware, Spray Calibration, Sensors & Safety Controls** | Cung cấp firmware, cảm biến, trạng thái slot và cơ chế an toàn; TP3 nhận dữ liệu và gửi lệnh qua giao thức thống nhất. |
| **TP4 – Customer Kiosk Interface, Fragrance Catalog, Order Workflow, QR Payment & Failure Recovery** | Sau khi backend xác minh thanh toán, TP4 phối hợp TP3 gửi lệnh xịt và nhận kết quả để cập nhật trạng thái đơn hàng hoặc xử lý lỗi. |
| **TP5 – Web Portal, Inventory, Maintenance, Reconciliation, Dashboard & Reporting** | TP3 cung cấp trạng thái máy, mức nước hoa ước tính, cảnh báo, sự kiện và kết quả lệnh để portal hiển thị, quản lý bảo trì và lập báo cáo. |
| **TP6 – End-to-End Integration, Security & Reliability Testing, Pilot, Deployment & Documentation** | Bàn giao gateway, MQTT, monitoring, commands, alerts và kết quả kiểm thử TP3 để tích hợp, kiểm thử bảo mật/độ tin cậy và triển khai toàn hệ thống. |

> **Trạng thái:** Tài liệu tổng quan phạm vi, công việc và đầu ra dự kiến; không khẳng định các hạng mục đã hoàn thành.
