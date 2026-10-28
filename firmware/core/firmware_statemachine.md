# TASK 2: THIẾT KẾ FIRMWARE ĐIỀU KHIỂN VÀ QUY ĐỊNH TRẠNG THÁI HOẠT ĐỘNG (STATE MACHINE)

## 1. Tổng quan Kiến trúc Firmware
Firmware đóng vai trò là lõi điều khiển phần cứng tại Kiosk, chịu trách nhiệm nhận lệnh, xác thực bảo mật, điều khiển các cơ van phun cho 5 slot nước hoa, giám sát cảm biến và duy trì an toàn vận hành. Dựa trên kiến trúc điều khiển an toàn của Kiosk ScentStation, Firmware được thiết kế dựa trên một Sơ đồ trạng thái máy (State Machine) cốt lõi bao gồm 4 trạng thái chính. Hệ thống đảm bảo tính nguyên vẹn của thiết bị, an toàn cho người dùng và tránh lãng phí dung dịch thông qua các điều kiện chuyển trạng thái nghiêm ngặt.

## 2. Định nghĩa các trạng thái hoạt động (Operating States)
Hệ thống (`enum class Mode`) được quy định bằng 4 trạng thái:
*   **IDLE (Chờ/Rảnh rỗi):** Trạng thái mặc định khi máy hoạt động bình thường. Toàn bộ các van phun đều đóng. Cảm biến liên tục lấy mẫu để theo dõi dung lượng và phát hiện rò rỉ. Máy sẵn sàng tiếp nhận lệnh từ server.
*   **DISPENSING (Đang phun):** Máy đang thực thi một lệnh xịt hợp lệ. Van của slot được chỉ định đang mở. Watchdog an toàn được kích hoạt để giám sát thời gian mở van.
*   **FAULT (Lỗi phần cứng):** Trạng thái khóa an toàn (Lockdown). Xảy ra khi hệ thống phát hiện sự cố nghiêm trọng (như rò rỉ dung dịch hoặc van không tự đóng). Ở trạng thái này, máy từ chối mọi lệnh phun thương mại để bảo vệ thiết bị.
*   **MAINTENANCE (Bảo trì):** Chế độ đặc quyền dành riêng cho kỹ thuật viên. Tại đây, kỹ thuật viên có thể thay chai, xịt thử nghiệm chẩn đoán lỗi (`DIAG_SPRAY`), và reset các cờ cảnh báo.

## 3. Diễn giải luồng đi của Sơ đồ (Visual Diagram Flow)

Nhìn vào sơ đồ thiết kế, vòng đời của máy diễn ra theo các luồng mũi tên như sau:
*   **Khởi động (Boot) → IDLE:** Điểm bắt đầu (chấm đen). Máy luôn thực hiện đóng van và nạp lại lịch sử (ledger) trước khi vào trạng thái IDLE để đảm bảo an toàn tuyệt đối.
*   **Luồng phục vụ khách (Vòng lặp IDLE ↔ DISPENSING):** Mũi tên đi khi lệnh hợp lệ được chấp nhận và máy chuyển sang dispensing để xịt nước hoa. Mũi tên về khi đã xịt xong và máy trả về kết quả như ok / failed / uncertain và quay lại IDLE chờ khách tiếp theo.
*   **Luồng bắt lỗi tự động (FAULT):** Đang ở IDLE nhưng đầu dò rò rỉ ướt. Đang ở DISPENSING nhưng bị rò rỉ giữa chừng hoặc van chạy quá giờ. Cả 2 trường hợp này đều lập tức đẩy mũi tên về FAULT và khóa máy.
*   **Luồng sửa chữa (→ MAINTENANCE → IDLE):** Kỹ thuật viên có thể vào maintenance từ lúc máy đang rảnh (IDLE) hoặc lúc máy đang bị lỗi (FAULT). Trong lúc bảo trì thì mũi tên tự chỉ vào chính nó thể hiện việc thợ có thể thao tác lặp lại nhiều lần (xịt thử `DIAG_SPRAY` hoặc lau khô đầu dò để xóa lỗi). Mũi tên thoát ra khi máy chỉ được trở về IDLE để tiếp tục kiếm tiền khi đã xịt thử thành công và không còn lỗi.

## 4. Quy định và điều kiện chuyển trạng thái chi tiết trong Code
Việc chuyển đổi giữa các trạng thái được kiểm soát bằng các hàm xử lý sự kiện và cảm biến vòng lặp (`tick()`):
*   **IDLE → DISPENSING:** Hàm `on_command()` kiểm tra 6 lớp bảo mật và nếu thỏa mãn thì `active_ = true`.
*   **DISPENSING → IDLE:** Hàm `finish()` ghi nhận lượng dung dịch thất thoát thực tế đo bằng cảm biến cân.
*   **DISPENSING → FAULT:** Hàm `tick()` kích hoạt khi phát hiện `leak_detected()` hoặc `elapsed > max_dose_ms`, gọi hàm `latch_fault()` để chốt lỗi.
*   **IDLE → FAULT:** Hàm `tick()` phát hiện rò rỉ lúc rảnh rỗi.
*   **IDLE / FAULT → MAINTENANCE:** Gọi hàm `enter_maintenance()`, đặt `maint_ = true`.
*   **MAINTENANCE → IDLE:** Gọi hàm `exit_maintenance()` và yêu cầu `fault_.empty()` và `diag_ok_ = true`.

## 5. Quy trình Kiểm duyệt An toàn Điều khiển (Safety Interlocks)
Ngoài vòng lặp trạng thái, mỗi lệnh điều khiển trước khi kích hoạt `DISPENSING` phải vượt qua các rào chắn bảo vệ từ Firmware:
1.  **Xác thực mật mã:** Chữ ký HMAC-SHA256 phải khớp, so sánh bằng thuật toán thời gian cố định `ct_equal` chống tấn công dò ngược mật khẩu.
2.  **Anti-Replay:** Lệnh phải nằm trong khung thời gian hẹp, không chấp nhận lệnh quá hạn hoặc từ tương lai.
3.  **Idempotency (Độc nhất):** Đối chiếu với Sổ cái (`Ledger`), một mã đơn hàng không bao giờ được xịt 2 lần.
4.  **Hardware Safety:** Cửa Kiosk phải đóng, nút dừng khẩn cấp không bị nhấn và không có chất lỏng rò rỉ dưới khay.