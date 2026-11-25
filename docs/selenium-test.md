## Báo cáo kiểm thử Selenium – Kiosk trải nghiệm nước hoa ScentStation
# 1. Tổng quan
- Hệ thống: ScentStation – Luồng trải nghiệm nước hoa tại Kiosk
- Loại kiểm thử: Kiểm thử giao diện end-to-end bằng Selenium WebDriver
- Môi trường kiểm thử: Mock Server
- Framework: pytest
- Kết quả: 6 test case đạt, 0 test case thất bại
- Thời gian thực thi: 43,95 giây
Các test case được thực thi trên giao diện Kiosk thông qua môi trường mô phỏng (Mock Server).

# 2. Tổng kết kết quả thực thi
Chỉ tiêu	Kết quả
Tổng số test case	6
Số test đạt (PASSED)	6
Số test thất bại (FAILED)	0
Thời gian thực thi	43,95 giây
Kết quả chung	ĐẠT

3 3. Chi tiết các test case
TC01 – Hiển thị lỗi khi Device Secret không hợp lệ
- Tên test: test_wrong_device_secret_shows_error
- Mục tiêu: Kiểm tra hệ thống hiển thị thông báo lỗi khi người dùng nhập Device Secret không hợp lệ.
- Kết quả mong đợi: Device Secret không hợp lệ bị từ chối và giao diện hiển thị thông báo lỗi.
- Kết quả thực tế: PASSED

TC02 – Chọn sản phẩm và xem chi tiết nước hoa
- Tên test: test_catalog_selection_and_perfume_details
- Mục tiêu: Kiểm tra người dùng có thể chọn nước hoa từ danh mục và xem thông tin chi tiết.
- Kết quả mong đợi: Việc chọn sản phẩm và xem chi tiết diễn ra đúng theo các bước được kiểm tra.
- Kết quả thực tế: PASSED

TC03 – Luồng trải nghiệm nước hoa / tạo đơn
- Tên test: Chưa xác nhận tên hàm chính xác từ output terminal.
- Mục tiêu: Kiểm tra luồng trải nghiệm và tạo đơn trên giao diện Kiosk.
- Kết quả mong đợi: Luồng trải nghiệm/tạo đơn hoàn tất theo các điều kiện được kiểm tra trong test.
- Kết quả thực tế: PASSED

TC04 – Thanh toán demo dẫn đến màn hình thành công
- Tên test: test_demo_payment_reaches_success_screen
- Mục tiêu: Kiểm tra luồng thanh toán demo dẫn đến màn hình thông báo thành công.
- Kết quả mong đợi: Màn hình thành công được hiển thị sau khi thực hiện luồng thanh toán demo.
- Kết quả thực tế: PASSED

TC05 – Lỗi chiết nước hoa không cho phép thanh toán lại
- Tên test: test_dispense_failure_does_not_offer_retry_payment
- Mục tiêu: Kiểm tra cách hệ thống xử lý khi quá trình chiết nước hoa thất bại và không đưa ra tùy chọn thanh toán lại.
- Kết quả mong đợi: Hệ thống xử lý trạng thái thất bại và không hiển thị tùy chọn thanh toán lại.
- Kết quả thực tế: PASSED

TC06 – Máy bị khóa hiển thị trạng thái không khả dụng
- Tên test: test_machine_blocked_displays_unavailable_screen
- Mục tiêu: Kiểm tra giao diện khi máy ở trạng thái bị khóa.
- Kết quả mong đợi: Giao diện hiển thị trạng thái máy không khả dụng.
- Kết quả thực tế: PASSED
# 4. Kết luận
Cả 6 test case Selenium đều đạt trong môi trường mô phỏng. Kết quả cho thấy các luồng giao diện được kiểm tra đáp ứng những điều kiện xác nhận (assertion) của bộ test trong lần thực thi này.