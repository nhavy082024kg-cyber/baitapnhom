# ĐẶC TẢ USE CASE - ScentStation

Mô tả toàn bộ 61 use case

## 2.1 Xác thực và phân quyền

| ID | Use Case | Actors | Use Case Description |
|---|---|---|---|
| UC-01 | Đăng nhập | Mọi người dùng nhân sự | Người dùng nhập tài khoản và mật khẩu. Hệ thống xác thực, xác định brand và vai trò rồi tạo phiên làm việc, đồng thời ghi nhận lần đăng nhập. Tài khoản bị khóa hoặc brand bị tạm ngưng thì bị từ chối. |
| UC-02 | Đăng xuất / thu hồi phiên | Mọi người dùng nhân sự; Platform Super Administrator | Người dùng kết thúc phiên làm việc của mình. Super Admin có thể thu hồi phiên đang hoạt động khi phát hiện bất thường. |
| UC-03 | Đặt lại mật khẩu | Mọi người dùng nhân sự | Người dùng yêu cầu đặt lại mật khẩu qua email đã đăng ký. Hệ thống gửi liên kết có thời hạn, cho phép đặt mật khẩu mới và vô hiệu các phiên cũ. |
| UC-04 | Xác thực bổ sung | Brand Administrator, Operations Manager, Technician, Inventory Staff | Yêu cầu người dùng xác nhận lại danh tính (mật khẩu hoặc mã xác thực) trước các thao tác nhạy cảm như hoàn tiền, điều chỉnh tồn kho, phun thử, đổi cấu hình slot. |

## 2.2 Quản trị nền tảng và brand

| ID | Use Case | Actors | Use Case Description |
|---|---|---|---|
| UC-05 | Quản lý tenant (brand) | Platform Super Administrator | Tạo, sửa, kích hoạt hoặc tạm ngưng brand (tenant). Dữ liệu mỗi brand được tách biệt hoàn toàn; brand đã có dữ liệu không được xóa cứng. |
| UC-06 | Quản lý Brand Admin | Platform Super Administrator | Tạo, sửa, khóa tài khoản Brand Administrator cho từng brand và gán họ vào đúng tenant. |
| UC-07 | Cấu hình nền tảng | Platform Super Administrator | Thiết lập cấu hình dùng chung toàn nền tảng gồm kênh thanh toán, chính sách hệ thống và thông báo. |
| UC-08 | Giám sát toàn bộ máy | Platform Super Administrator | Xem trạng thái, cảnh báo và hoạt động của mọi máy kiosk của tất cả brand trên nền tảng. |
| UC-09 | Xem và tìm audit log | Platform Super Administrator | Xem, lọc và tìm kiếm nhật ký kiểm toán của toàn nền tảng theo người dùng, thao tác, brand và thời gian. |
| UC-10 | Thu hồi quyền người dùng / thiết bị | Platform Super Administrator | Thu hồi quyền truy cập của người dùng hoặc thiết bị khi có hoạt động đáng ngờ. Thao tác có hiệu lực ngay và được ghi audit log. |
| UC-11 | Quản lý thông tin brand | Brand Administrator | Cập nhật thông tin brand và nội dung hiển thị trên kiosk (tên, mô tả, hình ảnh). |
| UC-12 | Quản lý người dùng và vai trò | Brand Administrator | Tạo, sửa, khóa tài khoản nhân sự trong brand; gán vai trò và phạm vi quyền theo địa điểm hoặc máy. |
| UC-13 | Quản lý sản phẩm nước hoa | Brand Administrator | Tạo, sửa, vô hiệu hóa sản phẩm nước hoa (tên, mô tả, giá, hình ảnh) của brand. |
| UC-14 | Quản lý địa điểm và gán máy | Brand Administrator | Quản lý các địa điểm đặt máy và gán máy kiosk vào từng địa điểm của brand. |
| UC-15 | Cấu hình slot máy | Brand Administrator | Cấu hình từng slot của máy: sản phẩm, giá, ngưỡng tồn kho, liều phun. Cần xác thực bổ sung. |
| UC-16 | Cấu hình khuyến mãi / giá tạm | Brand Administrator | Tạo, sửa, hủy khuyến mãi hoặc giá tạm thời cho sản phẩm trong khoảng thời gian xác định. |
| UC-17 | Xem và xuất báo cáo | Brand Administrator | Xem báo cáo doanh thu, giao dịch, hoạt động máy của brand và xuất ra tệp. |
| UC-18 | Cấu hình giờ hoạt động và ngưỡng cảnh báo | Brand Administrator | Đặt giờ bán hàng của máy, ngưỡng tồn kho thấp và các ngưỡng cảnh báo vận hành của brand. |
| UC-19 | Xem báo cáo thống kê toàn nền tảng | Platform Super Administrator | Xem thống kê tổng hợp của toàn nền tảng gồm doanh thu, số giao dịch, số máy và tình trạng hoạt động theo brand. |

## 2.3 Trải nghiệm tại kiosk

| ID | Use Case | Actors | Use Case Description |
|---|---|---|---|
| UC-20 | Xem danh sách mùi hương | Customer / Kiosk User | Khách xem danh sách mùi hương đang có trên máy cùng thông tin chi tiết (tên, mô tả, giá, tình trạng còn hàng). |
| UC-21 | Chọn mùi, xác nhận giá và tạo order | Customer / Kiosk User | Khách chọn một mùi hương và xác nhận giá. Hệ thống tạo order ở trạng thái chờ thanh toán, cố định mùi và giá tại thời điểm đó. |
| UC-22 | Thanh toán bằng QR | Customer / Kiosk User, Payment Provider | Hệ thống hiển thị mã QR động gắn với order. Khách quét và thanh toán; hệ thống theo dõi đến khi thanh toán thành công, thất bại hoặc hết hạn. |
| UC-23 | Nhận một lần phun | Customer / Kiosk User, IoT Device (Kiosk) | Sau khi backend xác nhận thanh toán, máy phun đúng một lần theo order và báo kết quả cho hệ thống và khách. |
| UC-24 | Xử lý khi đã trả tiền nhưng phun lỗi | Customer / Kiosk User | Khi thanh toán thành công nhưng phun thất bại hoặc không chắc chắn, kiosk hướng dẫn khách và chuyển giao dịch sang quy trình review hoặc hoàn tiền. Không tự phun lại. |
| UC-25 | Quét QR sản phẩm | Customer / Kiosk User | Khách quét mã QR trên sản phẩm để xem thông tin và khuyến mãi liên quan. |
| UC-26 | Xác minh webhook thanh toán | Payment Provider | Hệ thống nhận webhook từ nhà cung cấp thanh toán, kiểm tra chữ ký, mã tham chiếu, số tiền, tiền tệ, trạng thái và chặn xử lý trùng trước khi cập nhật order. |
| UC-27 | Gửi lệnh phun và nhận kết quả | IoT Device (Kiosk) | Hệ thống tạo lệnh phun có định danh, hạn dùng và chữ ký, gửi tới máy. Máy xác nhận, thực thi và trả kết quả; quá thời gian thì đánh dấu không chắc chắn. |
| UC-28 | Xem hướng dẫn trải nghiệm | Customer / Kiosk User | Kiosk hiển thị hướng dẫn cách nhận và cảm nhận mùi hương sau khi thanh toán. |

## 2.4 Vận hành và giao dịch

| ID | Use Case | Actors | Use Case Description |
|---|---|---|---|
| UC-29 | Đối soát giao dịch với nhà cung cấp thanh toán | Operations Manager, Payment Provider | So khớp giao dịch của hệ thống với dữ liệu của nhà cung cấp thanh toán để phát hiện chênh lệch và xử lý. |
| UC-30 | Giám sát trạng thái máy và slot | Operations Manager | Theo dõi trạng thái, cảnh báo, tồn kho của các máy và slot trong brand. |
| UC-31 | Bật / tắt máy hoặc slot từ xa | Operations Manager, Brand Administrator | Bật hoặc tắt một máy hay một slot từ xa, ví dụ khi có sự cố hoặc để ngừng bán tạm thời. |
| UC-32 | Xem và tìm kiếm giao dịch | Operations Manager | Xem danh sách giao dịch và tìm kiếm theo mã, thời gian, máy, trạng thái. |
| UC-33 | Xử lý giao dịch lỗi | Operations Manager | Xử lý giao dịch đã trả tiền nhưng phun lỗi hoặc chưa xác nhận: retry có kiểm soát, đưa vào review hoặc từ chối. Mọi thao tác ghi lý do. |
| UC-34 | Hoàn tiền | Operations Manager, Payment Provider | Thực hiện hoàn tiền cho giao dịch lỗi qua nhà cung cấp thanh toán. Cần xác thực bổ sung và ghi audit log. |
| UC-35 | Quản lý cảnh báo | Operations Manager | Xem, xác nhận, giao việc, đóng và mở lại các cảnh báo vận hành. |
| UC-36 | Tạo và giao ticket bảo trì | Operations Manager | Tạo ticket bảo trì, đặt mức ưu tiên và giao cho kỹ thuật viên. |
| UC-37 | Xem dashboard và báo cáo vận hành | Operations Manager | Xem dashboard tổng hợp về giao dịch, tình trạng máy và hiệu suất vận hành. |
| UC-38 | Nhận heartbeat và telemetry | IoT Device (Kiosk) | Hệ thống nhận tín hiệu sống và dữ liệu cảm biến từ máy đã đăng ký, cập nhật trạng thái máy. |
| UC-39 | Tạo cảnh báo và ticket tự động | IoT Device (Kiosk) (hệ thống) | Hệ thống tự tạo cảnh báo và ticket bảo trì khi dữ liệu máy vượt ngưỡng hoặc mất kết nối, có cơ chế tránh tạo trùng. |

## 2.5 Bảo trì máy

| ID | Use Case | Actors | Use Case Description |
|---|---|---|---|
| UC-40 | Xem máy, cảnh báo và ticket được giao | Technician | Kỹ thuật viên xem danh sách máy, cảnh báo và ticket bảo trì được giao cho mình. |
| UC-41 | Bật chế độ bảo trì | Technician | Chuyển máy sang chế độ bảo trì để chặn order mới trong khi sửa chữa. |
| UC-42 | Chẩn đoán máy / slot | Technician, IoT Device (Kiosk) | Chạy chẩn đoán trên máy hoặc slot để xác định nguyên nhân lỗi. |
| UC-43 | Phun thử (test spray) | Technician, IoT Device (Kiosk) | Phun thử để kiểm tra bơm, van, lưu lượng. Cần xác thực bổ sung; lần phun thử được ghi riêng và không trừ tồn kho bán hàng. |
| UC-44 | Thực hiện bảo trì theo checklist | Technician | Thực hiện và ghi nhận từng bước bảo trì, sửa chữa theo checklist. |
| UC-45 | Kiểm tra sau bảo trì | Technician, IoT Device (Kiosk) | Chạy kiểm tra bắt buộc sau bảo trì; chỉ khi đạt máy mới được hoạt động trở lại. |
| UC-46 | Đóng ticket bảo trì | Technician | Đóng ticket sau khi đã ghi kết quả bảo trì và kiểm tra đạt. |
| UC-47 | Xem lịch sử bảo trì và lỗi của máy | Technician, Operations Manager | Xem lịch sử bảo trì và các lỗi đã xảy ra của một máy. |

## 2.6 Tồn kho và nạp chai

| ID | Use Case | Actors | Use Case Description |
|---|---|---|---|
| UC-48 | Quản lý lô nước hoa | Inventory Staff | Tạo, sửa thông tin lô nước hoa (mã lô, số lượng, hạn dùng). |
| UC-49 | Đăng ký chai / cartridge | Inventory Staff | Đăng ký chai hoặc cartridge với mã định danh duy nhất. |
| UC-50 | Lắp / thay chai vào slot | Inventory Staff | Gán chai vào slot, vô hiệu chai cũ, ghi khối lượng trước và sau. Mỗi slot chỉ có một chai hoạt động. |
| UC-51 | Đối soát tồn kho với cảm biến | Inventory Staff, IoT Device (Kiosk) | So sánh tồn kho ước tính với dữ liệu cảm biến và ghi nhận chênh lệch. |
| UC-52 | Điều chỉnh tồn kho | Inventory Staff | Điều chỉnh tồn kho thủ công, bắt buộc có lý do và xác thực bổ sung; lịch sử điều chỉnh không bị sửa hay xóa. |
| UC-53 | Xem lịch sử và báo cáo tồn kho | Inventory Staff, Operations Manager | Xem lịch sử nhập, thay chai, điều chỉnh và báo cáo tồn kho. |
| UC-54 | Nhận cảnh báo tồn kho | Inventory Staff, Operations Manager | Nhận cảnh báo khi tồn kho sắp hết, tiêu hao bất thường hoặc chai sắp hết hạn. |
| UC-55 | Kiểm tra đúng mùi - đúng slot | Inventory Staff | Kiểm tra chai được lắp có đúng mùi hương của slot trước khi kích hoạt. |

## 2.7 Thiết bị IoT và an toàn

| ID | Use Case | Actors | Use Case Description |
|---|---|---|---|
| UC-56 | Xác thực thiết bị | IoT Device (Kiosk) | Thiết bị đăng ký và xác thực danh tính khi kết nối; thiết bị chưa đăng ký hoặc đã bị thu hồi bị từ chối. |
| UC-57 | Gửi sự kiện và mã lỗi thiết bị | IoT Device (Kiosk) | Máy gửi sự kiện, mã lỗi và cảnh báo phần cứng lên hệ thống. |
| UC-58 | Nhận và xác thực lệnh điều khiển | IoT Device (Kiosk) | Máy kiểm tra chữ ký, hạn dùng và mã lệnh; từ chối lệnh không hợp lệ hoặc đã dùng. |
| UC-59 | Kiểm tra điều kiện an toàn trước khi phun | IoT Device (Kiosk) | Máy kiểm tra các điều kiện an toàn (cửa, nhiệt độ, lỗi phần cứng, tồn kho, trạng thái) trước khi phun; không đạt thì không phun. |
| UC-60 | Dừng khẩn cấp và khóa cơ cấu khi lỗi | IoT Device (Kiosk), Operations Manager, Technician | Dừng ngay bơm và van, khóa slot hoặc máy theo mức lỗi. Mở khóa cần người có quyền, xác thực bổ sung và kiểm tra sau bảo trì đạt. |
| UC-61 | Lưu sự kiện khi mất mạng và đồng bộ lại | IoT Device (Kiosk) | Máy lưu sự kiện cục bộ khi mất kết nối và gửi lại đầy đủ khi có mạng. |
