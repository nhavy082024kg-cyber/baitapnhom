# THIẾT KẾ CƠ SỞ DỮ LIỆU VÀ SƠ ĐỒ ERD

## 1. Mục tiêu và Cơ sở lý thuyết
Dựa trên nguyên tắc kỹ nghệ yêu cầu (Requirements Engineering) việc thiết kế cơ sở dữ liệu (CSDL) phải phản ánh đúng các quy tắc nghiệp vụ và đảm bảo các thuộc tính chất lượng như tính bảo mật và toàn vẹn dữ liệu. Cấu trúc dữ liệu được thiết kế nhằm phục vụ nền tảng IoT ScentStation hoạt động theo mô hình đa khách hàng.

## 2. Mô hình Kiến trúc Dữ liệu Đa khách hàng (Multi-Tenant)
Hệ thống quản lý nhiều Brand trên cùng một hạ tầng cơ sở dữ liệu. Để giải quyết bài toán cách ly dữ liệu, kiến trúc CSDL áp dụng các nguyên tắc sau:
*   **Shared Schema - Isolated Data:** Tất cả các nhãn hàng dùng chung một schema cơ sở dữ liệu, nhưng mọi bảng nghiệp vụ đều bắt buộc có cột `tenant_id`[cite: 102].
*   **Bảo mật cấp độ dòng (Row-Level Security - RLS):** PostgreSQL RLS được kích hoạt (`ENABLE ROW LEVEL SECURITY` và `FORCE ROW LEVEL SECURITY`) trên các bảng để chặn tuyệt đối việc nhãn hàng này đọc hoặc sửa dữ liệu của nhãn hàng khác[cite: 102].
*   **Quản lý Ngữ cảnh Truy cập (Context-based Access):** Ứng dụng kết nối DB qua một role chung là `scent_app` (không phải superuser)[cite: 102]. Trước mỗi truy vấn, ứng dụng phải thiết lập ngữ cảnh:
    *   `set_config('app.tenant_id', '<uuid>', true)`: Định danh nhãn hàng đang truy cập[cite: 102].
    *   `set_config('app.bypass', 'on', true)`: Quyền truy cập toàn cục dành riêng cho quản trị nền tảng hệ thống (Platform Admin)[cite: 102].
    *   *Fail Closed:* Nếu không có ngữ cảnh nào được thiết lập, mọi truy vấn sẽ trả về 0 dòng dữ liệu, đảm bảo an toàn tuyệt đối khi có lỗi logic code[cite: 102, 104].

## 3. Thiết kế Sơ đồ ERD
Sơ đồ ERD mô tả cấu trúc các thực thể và mối quan hệ ràng buộc khép kín giữa chúng[cite: 105]:

### 3.1. Core Entities
*   **Tenants:** Bảng gốc lưu thông tin nhãn hàng (Dior, Gucci, Chanel...). Quản lý mã nhãn hàng, trạng thái hoạt động (`active`, `suspended`), và cấu hình hiển thị Kiosk[cite: 102, 105].
*   **Users & Roles (RBAC):** Quản lý người dùng, mật khẩu (mã hóa), và phân quyền. 
    *   `roles` và `permissions` định nghĩa quyền hạn ở cấp độ 'platform' hoặc 'tenant'[cite: 102, 105]. 
    *   Thực thể trung gian `user_roles` liên kết người dùng với vai trò, kèm theo phạm vi phân quyền cụ thể (`scope_type`: tenant, location, machine)[cite: 102, 105].

### 3.2. Business Entities
*   **Products:** Quản lý danh mục nước hoa của từng nhãn hàng. Chứa thông tin về giá mỗi lần xịt (`price_per_spray`), mùi hương (`fragrance_notes` dạng JSONB), và trạng thái khả dụng[cite: 102, 105].
*   **Locations & Machines:** Quản lý các điểm đặt Kiosk và thông tin cấu hình của từng thiết bị vật lý thuộc về nhãn hàng[cite: 102, 105].
*   **Vận hành Kiosk (Orders, Dispense, Slots):** Lưu trữ lịch sử đơn hàng, các lệnh phun nước hoa (Dispense Command), cấu hình khay chứa (Slots), và nhật ký thay bình (Refill Log)[cite: 105].

## 4. Các Ràng buộc Không gian Dữ liệu và Toàn vẹn 
Hệ thống thiết lập các ràng buộc chặt chẽ ngay tại tầng CSDL để ngăn chặn sai sót:
*   **Khóa ngoại kép (Composite Foreign Keys):** Thay vì chỉ liên kết bằng `id`, các bảng con liên kết với nhau bằng cặp khóa `(tenant_id, id)`. Điều này khiến việc tạo một bản ghi thuộc nhãn hàng A nhưng lại liên kết chéo với người dùng của nhãn hàng B là bất khả thi về mặt vật lý[cite: 102, 104].
*   **Nhật ký Kiểm toán (Audit Logs) dạng Append-only:** Bảng `audit_logs` lưu trữ mọi hành động thay đổi dữ liệu (actor_id, before_data, after_data). PostgreSQL Trigger được sử dụng để chặn hoàn toàn mọi lệnh `UPDATE`, `DELETE`, hoặc `TRUNCATE` trên bảng này, biến nó thành sổ cái bất biến (immutable)[cite: 102].
*   **Kiểm thử Cách ly Dữ liệu:** Các kịch bản kiểm thử (`test.sql`) đã chứng minh rằng người dùng của nhãn hàng A không thể thấy (`SELECT`), sửa (`UPDATE`), hay chèn (`INSERT`) dữ liệu của nhãn hàng B kể cả khi cố tình khai thác lỗ hổng ứng dụng[cite: 104].

## 5. Môi trường SQLite Hỗ trợ Kiểm thử Tự động 
Để hỗ trợ việc chạy Unit Test nhanh chóng và không phụ thuộc vào máy chủ PostgreSQL, một phiên bản CSDL SQLite (`init_sqlite_2.sql`) được thiết kế phản chiếu lại cấu trúc PostgreSQL[cite: 103]. 
*   Vì SQLite không hỗ trợ Row-Level Security (RLS) bản địa, sự cách ly dữ liệu ở môi trường này được bảo vệ tại tầng mã nguồn (Application Layer) thông qua lớp `TenantRepo`[cite: 103].
*   Các kiểu dữ liệu đặc thù được tinh chỉnh (ví dụ: `uuid`, `jsonb`, và thời gian được lưu dưới dạng `text`, `boolean` lưu bằng `integer 0/1`) để tương thích với engine của SQLite[cite: 103].