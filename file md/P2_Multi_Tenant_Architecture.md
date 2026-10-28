# TP1 – P2: Multi-Tenant Architecture (Kiến trúc đa thương hiệu)

## 1. Mục tiêu
Thiết kế kiến trúc để nhiều thương hiệu nước hoa dùng chung nền tảng ScentStation nhưng không truy cập trái phép dữ liệu của nhau.

## 2. Đầu ra cố định
1. **Sơ đồ kiến trúc Multi-Tenant.**
2. **Quy tắc cô lập dữ liệu.**

## 3. Sơ đồ kiến trúc Multi-Tenant

![Sơ đồ kiến trúc Multi-Tenant của ScentStation](../image(20261024-082156).png)

ScentStation sử dụng **một ứng dụng (Shared Application), một cơ sở dữ liệu PostgreSQL (Shared Database), một schema (Shared Schema)** cho tất cả thương hiệu. Mỗi thương hiệu là một **tenant**. Các bảng dữ liệu nghiệp vụ theo thương hiệu có cột `tenant_id`; PostgreSQL dùng **Row-Level Security (RLS)** để hạn chế đọc và sửa dữ liệu theo tenant đã xác thực.

**Lý do lựa chọn:**
- Thêm brand mới bằng cách thêm bản ghi vào bảng `tenants`, không cần tạo CSDL hoặc schema mới.
- Dùng chung một bộ bảng và một lần migration cho tất cả brand.
- Có thể thiết kế để tách một brand sang CSDL riêng về sau nếu cần, nhưng việc chuyển đổi vẫn cần kế hoạch migration và thay đổi cấu hình tích hợp.

**Phương án thay thế:** Mỗi tenant có CSDL riêng hoặc schema riêng. Các phương án này tăng mức tách biệt nhưng làm vận hành và migration phức tạp hơn khi số lượng brand tăng.

### 3.1. Phân cấp dữ liệu
```text
Nền tảng (Super Admin, cấu hình dùng chung)
└── Tenant (thương hiệu)
    ├── Người dùng, vai trò, phạm vi
    ├── Sản phẩm
    └── Địa điểm
        └── Máy
            └── Slot (gắn sản phẩm và giá)
```

### 3.2. Xác định tenant của một yêu cầu
| Nguồn yêu cầu | Tenant được xác định từ |
|---|---|
| Người dùng Portal | Claim `tenant_id` trong token đã ký và đã được xác minh |
| Kiosk của khách hàng | Danh tính máy đã đăng ký và gắn với đúng một tenant |
| Thiết bị qua MQTT | Danh tính thiết bị được xác thực, đối chiếu với tenant và quyền truy cập topic |
| Webhook thanh toán | Mã tham chiếu thanh toán tra về đơn hàng chứa `tenant_id`, sau khi xác minh webhook |
| Super Admin | Dùng API và quyền quản trị nền tảng riêng, có kiểm soát và audit |

## 4. Quy tắc cô lập dữ liệu (Tenant Data Isolation Rules)

1. **Dữ liệu có chủ sở hữu tenant:** Mỗi bản ghi nghiệp vụ theo brand có `tenant_id NOT NULL` và tham chiếu tenant hợp lệ.
2. **Không tin tenant từ client:** Không dùng trực tiếp `tenant_id` trong URL, body hoặc MQTT topic làm căn cứ cấp quyền; phải đối chiếu danh tính đã xác thực.
3. **Mặc định từ chối:** Không xác định được tenant hợp lệ thì không cho phép truy cập dữ liệu tenant.
4. **Cách ly nhiều lớp:** Danh tính, backend, PostgreSQL, cache, MQTT và audit phối hợp bảo vệ dữ liệu.
5. **Không liên kết chéo tenant:** Các quan hệ dữ liệu giữa bảng thuộc tenant phải được kiểm tra cùng `tenant_id`, ưu tiên ràng buộc khóa ngoại ghép khi phù hợp.
6. **Dữ liệu dùng chung:** Tách khỏi dữ liệu tenant và chỉ cấp quyền theo nhu cầu.
7. **Super Admin:** Quyền nền tảng tách riêng; các thao tác nhạy cảm phải được ghi audit.
8. **Định danh tenant xuyên suốt:** Cache, MQTT, nhật ký và tác vụ nền cần gắn hoặc xác minh tenant tương ứng.

### 4.1. Các lớp bảo mật
| Lớp | Nơi áp dụng | Cơ chế | Mục đích |
|---|---|---|---|
| 1 | Danh tính | Token đã ký hoặc danh tính/chứng chỉ thiết bị được xác minh | Chặn giả mạo tenant |
| 2 | Backend | Xác lập tenant context tin cậy và kiểm tra RBAC trên từng yêu cầu | Chặn truy cập ngoài tenant hoặc ngoài vai trò |
| 3 | PostgreSQL | RLS cho bảng dữ liệu tenant; role ứng dụng không có `BYPASSRLS`, không dùng quyền chủ bảng để vượt RLS | Hạn chế rò rỉ dữ liệu khi truy vấn thiếu điều kiện tenant |
| 4 | Redis / Cache (nếu sử dụng) | Tiền tố khóa `t:{tenant_id}:` và kiểm soát quyền truy cập | Tránh lẫn cache, khóa idempotency giữa brand |
| 5 | MQTT | Topic `scentstation/{tenant}/{machine}/...` và ACL ràng buộc theo danh tính thiết bị | Ngăn thiết bị đọc/ghi topic ngoài quyền |
| 6 | Audit | Ghi thao tác nhạy cảm và các lần truy cập bị từ chối | Truy vết hành vi vượt quyền |

**Lưu ý triển khai RLS:** Backend phải thiết lập tenant context từ danh tính tin cậy trong phạm vi giao dịch; dùng kết nối được trả về pool phải xóa/reset context để tránh rò rỉ sang yêu cầu tiếp theo. Với các bảng có tenant, chính sách RLS cần kiểm soát cả đọc lẫn ghi (ví dụ `USING` và `WITH CHECK`).

## 5. Kết luận
P2 chỉ bàn giao **sơ đồ kiến trúc Multi-Tenant** và **quy tắc cô lập dữ liệu**. Phần triển khai SQL DDL, Authentication/RBAC và API thuộc các phần công việc tương ứng, không tính là đầu ra bổ sung của P2.
