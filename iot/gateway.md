# THIẾT KẾ VÀ TRIỂN KHAI PHÂN HỆ IOT GATEWAY

## 1. Tổng quan Kiến trúc Phân hệ IoT Gateway
Trong hệ sinh thái Kiosk tự động ScentStation, IoT Gateway đóng vai trò là  trung tâm duy nhất giao tiếp giữa thiết bị phần cứng (Embedded Kiosk) và hạ tầng dịch vụ Đám mây (Cloud Backend). 

Được thiết kế theo kiến trúc **Zero-Trust (Không tin cậy bất kỳ ai)**, Gateway hoàn toàn tách biệt với giao thức truyền tải lõi. Nó không trực tiếp quản lý kết nối MQTT mà hoạt động như một bộ lọc an ninh tối cao: Nhận thông điệp dạng `(topic, payload, client_id)`, kiểm duyệt an toàn, ghi nhận trạng thái sống (heartbeat), và định tuyến (routing) dữ liệu đến các phân hệ xử lý nghiệp vụ thông qua cơ chế Hook mà không làm thay đổi mã nguồn cốt lõi.

## 2. Mô hình Bảo mật & Quy trình Kiểm duyệt 8 Bước (Validation Pipeline)
Để chống lại các nguy cơ tấn công mạng (như Spoofing - giả mạo thiết bị, DDoS - làm ngập lụt mạng, hay chèn mã độc), hàm `gw.handle()` tích hợp một chuỗi kiểm duyệt 8 bước tuần tự. Bất kỳ thông điệp nào vi phạm sẽ bị từ chối ngay lập tức, hệ thống tự động ghi log vào bảng `gateway_audit` và không làm thay đổi dữ liệu thật:

1. **BAD_TOPIC**: Định dạng chủ đề MQTT phải tuân thủ tuyệt đối cấu trúc `ss/<tenant_code>/<device_id>/<leaf>`. Chặn mọi truy vấn chứa ký tự đại diện nguy hiểm (`+`, `#`) hoặc các thư mục ảo (`..`, `/`).
2. **UNKNOWN_DEVICE**: Truy vấn cơ sở dữ liệu (`machines`), đảm bảo mã `device_id` đã được khai báo trên hệ thống.
3. **IDENTITY_MISMATCH**: Đối chiếu chéo `client_id` (đã được Broker xác thực) với `device_id` trên topic. Lớp bảo vệ này ngăn chặn triệt để hành vi máy A hợp lệ nhưng cố tình gửi data giả mạo vào topic của máy B.
4. **DEVICE_REVOKED**: Kiểm tra cờ trạng thái. Nếu máy đã bị đánh dấu là mất cắp hoặc xâm nhập (`revoked`), mọi thông điệp lập tức bị ném bỏ.
5. **TENANT_MISMATCH**: Đối chiếu mã nhãn hàng (Brand) trong topic với mã Brand thực tế đang sở hữu thiết bị này trong CSDL.
6. **TENANT_SUSPENDED**: Đảm bảo nhãn hàng quản lý thiết bị vẫn đang trong trạng thái hoạt động (`active`).
7. **PAYLOAD_TOO_LARGE**: Thiết lập giới hạn cứng `max_payload_bytes` (16 KB) để ngăn chặn tấn công tràn bộ đệm hoặc làm nghẽn băng thông hệ thống.
8. **BAD_PAYLOAD**: Sử dụng thư viện `Pydantic` (tại `schemas.py`) để ép kiểu dữ liệu JSON khắt khe. Các trường lạ (extra fields) sẽ bị bỏ qua, trong khi các trường sai kiểu hoặc vượt quá giới hạn (ví dụ lượng nước hoa âm) sẽ khiến tin nhắn bị loại bỏ.

## 3. Quản lý Danh tính và Cơ chế Cấp phát Chứng chỉ (Registry)
Tầng bảo mật của Gateway được thiết kế với tiêu chuẩn an toàn mật mã cao nhất:
* **Cấp phát 1 lần (One-time Display)**: Khi đăng ký máy mới, hệ thống dùng thuật toán ngẫu nhiên an toàn (`secrets.token_urlsafe`, `secrets.token_hex`) để sinh ra mật khẩu MQTT và Khóa ký lệnh (Command Key). Thông tin này chỉ hiển thị **duy nhất một lần** trên API cho kỹ thuật viên.
* **Bảo mật lưu trữ**: Gateway không bao giờ lưu trữ mật khẩu gốc mà chỉ lưu bản băm (Hash SHA-256) vào bảng `device_credentials`.
* **Chống tấn công Side-Channel (Timing Attack)**: Trong quá trình thiết bị đăng nhập, hàm `authenticate()` sử dụng `hmac.compare_digest` để so sánh chuỗi với hằng số thời gian. Kể cả khi thiết bị không tồn tại, hàm vẫn tiêu tốn lượng thời gian tính toán tương đương, giúp che giấu thông tin kiến trúc trước các hacker dò quét.

## 4. Tầng API Quản trị và Tích hợp Phân hệ (Integration Hooks)
Gateway cung cấp một lớp API HTTP bằng Flask, bảo vệ bằng các Token (`X-Gateway-Secret` và `X-Admin-Token`) nhằm phục vụ giao tiếp chéo giữa các phân hệ:

* **Tích hợp với P2 (MQTT Broker)**: 
  * Broker MQTT được ủy quyền gọi các Webhook xác thực thông qua API `/iot/auth` và phân quyền qua `/iot/acl`.
  * Khi Broker nhận tin nhắn từ thiết bị, nó đẩy dữ liệu thẳng vào Gateway thông qua hàm xử lý trung tâm: `gw.handle(topic, payload, client_id)`.
* **Tích hợp với P4 (Remote Command - Điều khiển từ xa)**: 
  * Khi P4 cần gửi lệnh xuống máy (ví dụ lệnh xịt), nó sẽ gọi hàm `registry.command_key(db, machine_id)` để lấy khóa HMAC ký bảo mật lên gói tin.
* **Tích hợp với P6 (Integration Testing)**: 
  * Hỗ trợ API `POST /iot/ingest` mô phỏng đầu vào của Broker. Điều này cho phép P6 bơm dữ liệu giả lập và kiểm thử toàn bộ luồng Backend mà không cần cài đặt hoặc khởi động Broker MQTT thực tế.
* **Kiến trúc Plugin (Event Handlers)**: Thông qua phương thức `gw.register_handler("telemetry", fn)`, các hệ thống con (P3, P4, P5) có thể chủ động "lắng nghe" và nhận dữ liệu mà không cần sửa đổi mã nguồn gốc của Gateway. Nếu một handler bị lỗi (crash), Gateway sẽ cô lập lỗi (rollback DB của handler) nhưng vẫn duy trì ghi nhận trạng thái sống (heartbeat) của Kiosk.

## 5. Đảm bảo Chất lượng Mã nguồn (Automated Testing & Demonstration)
Sự ổn định của hệ thống được chứng minh thông qua quy trình kiểm thử tự động khép kín:
* **Bộ Unit Test (`test_gateway.py`)**: Sử dụng CSDL SQLite lưu trữ trong bộ nhớ tạm (`tempfile`) kết hợp với kỹ thuật giả lập thời gian (`FakeClock`), đảm bảo mọi kịch bản kiểm thử đều độc lập và tái lập chính xác. Bao phủ mọi trường hợp ngoại lệ từ đăng ký trùng lặp, giả mạo thiết bị, gửi tin lặp (Duplicate events), đến thu hồi khóa.
* **Kịch bản Vận hành (`demo.py`)**: Tệp thực thi độc lập thể hiện vòng đời toàn cảnh của mạng lưới IoT: từ khởi tạo 5 nhãn hàng, đăng ký 5 kiosk, mô phỏng thiết bị bắn dữ liệu định kỳ, chặn đứng nỗ lực chèn ép dữ liệu sai schema, cho đến thao tác thu hồi khẩn cấp một thiết bị bị mất cắp. Tất cả diễn ra mượt mà không phụ thuộc vào hạ tầng bên thứ ba.