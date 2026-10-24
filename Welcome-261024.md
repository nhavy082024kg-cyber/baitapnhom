PHÂN TÍCH ĐỀ TÀI SCENTSTATION
1. Phân tích đề tài và xác định mục tiêu
Giới thiệu đề tài
ScentStation là dự án xây dựng hệ thống trải nghiệm và quản lý nước hoa thông qua các máy bán hàng tự động có kết nối IoT.

Hệ thống cho phép khách hàng lựa chọn mùi hương trên màn hình, thanh toán bằng mã QR và nhận một lần xịt nước hoa sau khi giao dịch được xác nhận thành công.

Một máy có thể chứa nhiều loại nước hoa khác nhau, trong đó mỗi vị trí chứa được điều khiển riêng biệt. Nhờ đó hệ thống có thể quản lý từng sản phẩm và kiểm soát quá trình xịt chính xác hơn.

Ngoài chức năng phục vụ khách hàng, hệ thống còn có nền tảng quản lý trực tuyến dành cho các thương hiệu nước hoa, hỗ trợ:

Theo dõi máy
Quản lý sản phẩm
Quản lý tồn kho
Quản lý đơn hàng
Giám sát tình trạng hoạt động thiết bị
Dữ liệu giữa các thương hiệu được tách biệt để đảm bảo quyền riêng tư và bảo mật.

Vấn đề cần giải quyết
Việc quản lý thủ công gây khó khăn trong:

Theo dõi lượng nước hoa còn lại
Giám sát tình trạng thiết bị
Kiểm soát giao dịch thanh toán
Đảm bảo một đơn hàng chỉ được xịt một lần
Ngoài ra hệ thống cần:

Tách biệt dữ liệu giữa nhiều thương hiệu
Hỗ trợ kỹ thuật viên phát hiện và xử lý sự cố
Hỗ trợ vận hành và bảo trì thiết bị hiệu quả
Mục tiêu hệ thống
Đối với khách hàng
Chọn mùi hương dễ dàng
Thanh toán QR tiện lợi
Trải nghiệm nước hoa nhanh chóng
Đối với thương hiệu
Quản lý sản phẩm
Quản lý máy
Quản lý đơn hàng
Quản lý tồn kho
Đối với vận hành
Theo dõi trạng thái thiết bị
Phát hiện lỗi
Hỗ trợ bảo trì
Đối với thanh toán
Chỉ cho phép xịt sau khi giao dịch được xác nhận thành công
Đối với bảo mật
Phân quyền người dùng
Tách biệt dữ liệu giữa các thương hiệu
Đối với kiểm soát
Lưu vết các hoạt động quan trọng
Hỗ trợ kiểm tra và đối soát
2. Phạm vi hệ thống
Các phân hệ chính
Phân hệ	Nội dung
Máy bán nước hoa	Quản lý các vị trí chứa và điều khiển độc lập
Giao diện khách hàng	Chọn sản phẩm và thanh toán
Quản lý đơn hàng	Theo dõi trạng thái giao dịch
Thanh toán	Xác minh giao dịch QR
Quản lý thương hiệu	Quản lý thông tin thương hiệu
Quản lý thiết bị	Theo dõi trạng thái và cấu hình
Quản lý tồn kho	Kiểm kê và bổ sung nước hoa
Bảo trì	Ghi nhận và xử lý lỗi
Báo cáo	Đối soát giao dịch và vận hành
Bảo mật	Phân quyền và nhật ký hệ thống
Giới hạn phạm vi
Dự án tập trung vào:

Nền tảng phần mềm
Quy trình quản lý
Kết nối với thiết bị IoT
Các nội dung chưa xác định cụ thể:

Nhà cung cấp thanh toán
Mẫu phần cứng cuối cùng
Quy mô triển khai thực tế
Chỉ tiêu hiệu năng chi tiết
3. Tác nhân hệ thống
STT	Tác nhân	Nhiệm vụ
1	Platform Super Administrator	Quản lý toàn bộ nền tảng
2	Brand Administrator	Quản lý thương hiệu
3	Operations Manager	Theo dõi vận hành
4	Technician	Bảo trì và xử lý sự cố
5	Inventory Staff	Quản lý tồn kho
6	Customer / Kiosk User	Sử dụng máy
7	IoT Machine	Gửi trạng thái và nhận lệnh
8	QR Payment Provider	Xử lý thanh toán
4. Quy tắc nghiệp vụ
Mã	Quy tắc
BR01	Mỗi máy chỉ thuộc một thương hiệu
BR02	Mỗi vị trí chỉ gắn một chai nước hoa
BR03	Chỉ hiển thị sản phẩm còn hoạt động
BR04	Giá bán được cố định tại thời điểm tạo đơn
BR05	Phải xác minh thanh toán từ nguồn hợp lệ
BR06	Chỉ xịt sau khi thanh toán thành công
BR07	Một đơn hàng chỉ được xịt tối đa một lần
BR08	Từ chối lệnh không hợp lệ hoặc trùng lặp
BR09	Không xịt khi máy đang lỗi hoặc bảo trì
BR10	Mất kết nối backend thì không nhận đơn mới
BR11	Chỉ trừ tồn kho sau khi xịt thành công
BR12	Xịt bảo trì phải được ghi nhận riêng
BR13	Ghi nhật ký các thao tác quan trọng
BR14	Giới hạn truy cập theo quyền
BR15	Kết quả xịt chưa rõ phải đưa vào đối soát
BR16	Chỉ hoạt động lại sau khi hoàn tất kiểm tra bảo trì
5. Yêu cầu chức năng
Mã	Chức năng
FR01	Quản lý thương hiệu
FR02	Quản lý tài khoản
FR03	Phân quyền
FR04	Quản lý sản phẩm
FR05	Quản lý máy và vị trí chứa
FR06	Giao diện khách hàng
FR07	Quản lý đơn hàng
FR08	Xử lý thanh toán
FR09	Điều khiển xịt nước hoa
FR10	Ghi nhận kết quả xịt
FR11	Giám sát thiết bị IoT
FR12	Quản lý tồn kho
FR13	Cảnh báo sự cố
FR14	Quản lý bảo trì
FR15	Đối soát giao dịch
FR16	Dashboard và báo cáo
FR17	Xuất báo cáo
FR18	Nhật ký hoạt động
FR19	Thông báo
FR20	Quản lý cấu hình thiết bị
6. Yêu cầu phi chức năng
Mã	Yêu cầu	Mô tả
NFR01	Hiệu năng	Độ trễ thấp khi thanh toán và giám sát
NFR02	Tính sẵn sàng	Ngăn giao dịch khi máy không đủ điều kiện
NFR03	Bảo mật	Phân quyền và bảo vệ dữ liệu
NFR04	Độ tin cậy	Một đơn hàng chỉ tạo tối đa một lần xịt
NFR05	Khả năng mở rộng	Hỗ trợ tăng số lượng máy và thương hiệu
NFR06	Dễ sử dụng	Giao diện rõ ràng, dễ thao tác
NFR07	Khả năng bảo trì	Hỗ trợ kiểm tra và xử lý lỗi
NFR08	An toàn thiết bị	Kiểm tra điều kiện an toàn trước khi xịt
Kết luận
ScentStation là hệ thống bán và trải nghiệm nước hoa thông minh kết hợp:

IoT
QR Payment
Multi-Tenant Management
Inventory Management
IoT Monitoring
Audit Logging
Mục tiêu là xây dựng nền tảng giúp tự động hóa quy trình bán hàng, quản lý thiết bị và hỗ trợ vận hành hiệu quả cho nhiều thương hiệu nước hoa