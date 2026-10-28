# ScentStation - XÁC ĐỊNH CÁC TÁC NHÂN (ACTORS)

| STT | Actor | Description |
|---|---|---|
| 1 | Platform Super Administrator (SA) | Quản trị viên toàn nền tảng. Tạo và quản lý các brand (tenant) và tài khoản Brand Admin, cấu hình nền tảng, giám sát và xem thống kê toàn bộ máy của mọi brand, xem audit log và thu hồi quyền người dùng hoặc thiết bị khi có hoạt động đáng ngờ. |
| 2 | Brand Administrator (BA) | Quản trị viên của một brand. Quản lý thông tin brand, nhân sự và phân quyền, sản phẩm nước hoa, địa điểm và máy, cấu hình slot, khuyến mãi, giờ hoạt động, ngưỡng cảnh báo và xem báo cáo. Chỉ làm việc trong phạm vi brand của mình. |
| 3 | Operations Manager (OM) | Quản lý vận hành. Giám sát trạng thái máy và slot, bật hoặc tắt máy từ xa, tra cứu và xử lý giao dịch lỗi, hoàn tiền, đối soát thanh toán, quản lý cảnh báo, tạo và giao ticket bảo trì, xem dashboard vận hành. Có thể dừng khẩn cấp máy từ xa. |
| 4 | Technician (TE) | Kỹ thuật viên bảo trì. Xem máy, cảnh báo và ticket được giao, bật chế độ bảo trì, chẩn đoán máy, phun thử, thực hiện bảo trì theo checklist, kiểm tra sau bảo trì và đóng ticket. Chỉ thao tác trên máy được giao. |
| 5 | Inventory Staff (IS) | Nhân viên kho và nạp chai. Quản lý lô nước hoa, đăng ký chai hoặc cartridge, lắp và thay chai vào slot, đối soát tồn kho với cảm biến, điều chỉnh tồn kho (có lý do) và xem lịch sử, báo cáo, cảnh báo tồn kho. |
| 6 | Customer / Kiosk User (CU) | Khách hàng ẩn danh tại kiosk, không có tài khoản. Xem danh sách mùi hương, chọn mùi và tạo đơn, thanh toán bằng QR, nhận một lần phun, quét QR sản phẩm, xem hướng dẫn trải nghiệm và nhận hướng dẫn khi đã trả tiền nhưng phun lỗi. |
| 7 | Payment Provider (PP) | Hệ thống bên ngoài xử lý thanh toán QR. Gửi webhook kết quả thanh toán (được hệ thống xác minh chữ ký, số tiền, trùng lặp), thực hiện hoàn tiền và cung cấp dữ liệu để đối soát giao dịch. |
| 8 | IoT Device (Kiosk) (DV) | Bộ điều khiển phần cứng của máy kiosk (hệ thống bên ngoài). Xác thực với hệ thống, gửi heartbeat, telemetry, sự kiện và mã lỗi, nhận và kiểm tra lệnh có chữ ký, kiểm tra điều kiện an toàn trước khi phun, thực hiện phun, dừng khẩn cấp và khóa khi lỗi, lưu sự kiện khi mất mạng và đồng bộ lại. |

