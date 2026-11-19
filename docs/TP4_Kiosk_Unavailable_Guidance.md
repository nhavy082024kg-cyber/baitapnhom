\### 5.3. Theo dõi trạng thái đơn hàng



\- Method: GET

\- Endpoint: `/api/v1/kiosk/orders/{order\_code}`



API trả về trạng thái đơn hàng và thông báo hướng dẫn tương ứng với từng trạng thái như chờ thanh toán, đã thanh toán, đang phun, phun thành công hoặc phun thất bại.



\## 6. Các thành phần code liên quan



| Thành phần | Chức năng |

|---|---|

| `src/domain/models/dispense\_policy.py` | Kiểm tra trạng thái kết nối và điều kiện hoạt động của máy, khe sản phẩm |

| `src/domain/models/settings.py` | Khai báo các ngưỡng cấu hình heartbeat |

| `src/config.py` | Đọc cấu hình từ biến môi trường |

| `src/services/order\_service.py` | Xử lý danh sách sản phẩm, kiểm tra điều kiện tạo đơn và thông báo trạng thái đơn hàng |

| `src/api/controllers/kiosk\_controller.py` | Cung cấp các API dành cho kiosk |



\## 7. Kiểm thử



Các trường hợp đã có trong bộ kiểm thử `tests/test\_business\_flows.py`:



\- Máy offline không được tạo đơn.

\- Máy đang bảo trì không được tạo đơn.

\- Máy có cảnh báo nghiêm trọng không được tạo đơn.

\- Khe sản phẩm hết hàng không được tạo đơn.

\- Khe sản phẩm không tồn tại không được tạo đơn.

\- Khe sản phẩm bị vô hiệu hóa không được tạo đơn.

\- Kiểm tra danh sách sản phẩm và quyền truy cập trạng thái đơn hàng của kiosk.



Các kiểm thử trên xác nhận việc kiểm soát điều kiện nhận đơn. Việc kiểm thử nội dung thông báo hướng dẫn cụ thể và giao diện hiển thị trên kiosk cần được xác nhận riêng.



\## 8. Kết luận



TP4 bổ sung khả năng kiểm tra điều kiện sẵn sàng của kiosk và cung cấp lý do khi hệ thống không cho phép tiếp nhận đơn hàng. Việc kiểm tra ở backend giúp hạn chế tạo đơn trong các tình huống máy mất kết nối, bảo trì, có lỗi nghiêm trọng hoặc khe sản phẩm không đáp ứng điều kiện.



Các API catalog và order status cung cấp dữ liệu cần thiết để kiosk đưa ra thông tin hướng dẫn phù hợp cho người dùng.

