# TASK PACKAGE 1 — TỔNG QUAN
## Phân tích hệ thống, kiến trúc Multi-Tenant, cơ sở dữ liệu, xác thực và quản trị thương hiệu

### 1. Mục tiêu
Xây dựng nền tảng thiết kế và quản lý dữ liệu cho ScentStation, cho phép nhiều thương hiệu nước hoa hoạt động trên cùng hệ thống nhưng chỉ truy cập dữ liệu được cấp quyền.
## Giai3 thích thuật ngữ 
| Thuật ngữ | Giai thích cơ bản|
|---|---|
| Tenant|một khách thuê của hệ thống mỗi brand là một tenant|
| Multi-tenant |nhiều brand dùng chung một hệ thống nhưng dữ liệu tách biệt|
| ERD |Entity Relationship Diagram/sơ đồ bảng dữ liệu và quan hệ giữa chúng|
| RBAC|Role-Based Access Control- Phân quyền theo vai trò |
| Authentication|Xác thực: "bạn là ai?" (đăng nhập)|
| Authorization	| Phân quyền: "bạn được làm gì|
|
### 2. Phạm vi công việc
- Phân tích yêu cầu chức năng, phi chức năng, tác nhân và quy tắc nghiệp vụ.
- Xây dựng Use Case Diagram và đặc tả các trường hợp sử dụng chính.
- Thiết kế kiến trúc hệ thống và mô hình multi-tenant; xác định cách ly dữ liệu theo tenant.
- Thiết kế ERD, bảng dữ liệu, khóa và các ràng buộc liên quan đến thương hiệu, người dùng, máy, slot và hoạt động.
- Thiết kế xác thực, phân quyền theo vai trò (RBAC), phạm vi truy cập và nhật ký kiểm toán.
- Thiết kế chức năng quản trị thương hiệu, tài khoản, vai trò và cấu hình cơ bản.

### 3. Thành phần chính
| Thành phần | Chức năng |
|---|---|
| Phân tích yêu cầu | Xác định nhu cầu của khách hàng và nhân sự vận hành |
| Multi-Tenant | Cách ly dữ liệu giữa các thương hiệu |
| Cơ sở dữ liệu | Lưu trữ và liên kết dữ liệu nghiệp vụ |
| Authentication / Authorization | Đăng nhập, xác thực và kiểm soát quyền |
| Brand Administration | Quản lý thương hiệu, tài khoản và phạm vi quản trị |

### 4. Quy tắc quan trọng
- Người dùng của thương hiệu này không được phép truy cập dữ liệu của thương hiệu khác .
- Máy thuộc một tenant tại một thời điểm; slot chỉ có một chai/hộp nước hoa đang hoạt động.
- Những thay đổi nhạy cảm về quyền, cấu hình và dữ liệu phải có nhật ký kiểm toán.
- Chỉ người có quyền mới được thực hiện các thao tác quản trị.

### 5. Đầu ra dự kiến
- Tài liệu yêu cầu và quy tắc nghiệp vụ.
- Use Case Diagram và đặc tả Use Case.
- Sơ đồ kiến trúc multi-tenant, quy tắc cô lập dữ liệu.
- ERD và SQL DDL tạo cấu trúc dữ liệu.
- Thiết kế luồng đăng nhập, phân quyền và chức năng quản trị thương hiệu.
- Kịch bản kiểm thử quyền truy cập giữa các tenant.

### 6. Tiêu chí nghiệm thu đề xuất
- Mô hình dữ liệu biểu diễn được thương hiệu, người dùng, máy và slot.
- Các vai trò có phạm vi quyền rõ ràng; thử nghiệm truy cập chéo tenant bị từ chối.
- Có tài liệu giải thích kiến trúc, bảng dữ liệu và luồng xác thực.
