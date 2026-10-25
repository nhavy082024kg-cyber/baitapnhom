# TASK PACKAGE 2 — TỔNG QUAN
## Kiosk Hardware Prototype, Embedded Firmware, Spray Calibration, Sensors and Safety Controls
### Prototype phần cứng kiosk, firmware nhúng, hiệu chuẩn lượng xịt, cảm biến và an toàn

### 1. Mục tiêu
Thiết kế, lắp ráp hoặc mô phỏng một kiosk trải nghiệm nước hoa **tối thiểu 4 slot điều khiển độc lập**. Mỗi slot có thể được chọn và kiểm tra riêng, thực hiện một chu trình xịt được hiệu chuẩn theo lệnh hợp lệ, đồng thời bảo đảm khóa an toàn khi có sự cố. TP2 phụ trách phần thiết bị và firmware; TP3 phụ trách gateway, MQTT, giám sát và cảnh báo phía hệ thống.

### Giải thích thuật ngữ
| Thuật ngữ | Giải thích cơ bản |
|---|---|
| Kiosk | Máy cho khách trải nghiệm nước hoa |
| Slot | Khe/vị trí chứa và điều khiển một loại nước hoa |
| Actuator | Cơ cấu chấp hành, ví dụ bơm hoặc van điều khiển xịt |
| Embedded firmware | Chương trình chạy trên bộ điều khiển nhúng, ví dụ ESP32 |
| State Machine | Sơ đồ trạng thái và điều kiện chuyển giữa các trạng thái máy |
| Sensor | Cảm biến đo hoặc phát hiện trạng thái máy |
| Calibration | Hiệu chuẩn lượng xịt để một chu trình đạt mức đã đặt |
| Interlock | Liên động an toàn: tự chặn hoạt động khi không đủ điều kiện |
| Prototype | Mẫu thử phần cứng hoặc mô phỏng chức năng |
| ACK | Phản hồi xác nhận đã nhận lệnh, không đồng nghĩa xịt thành công |

### 2. Phạm vi công việc — 6 phần (P1–P6)

#### P1 — Thiết kế 5 slot độc lập (Hardware Design)
**Công việc (Tasks)**
- Thiết kế tối thiểu 4 slot điều khiển riêng, cơ cấu bơm/van và bố trí phần cứng.
- Xác định nguồn điện, chân kết nối và cách tránh kích hoạt nhầm slot.

**Đầu ra (Deliverables):** Sơ đồ phần cứng, sơ đồ đấu nối 5  slot, danh sách linh kiện.

**Tiêu chí hoàn thành:** Có thiết kế rõ ràng cho 5 slot độc lập.

#### P2 — Thiết kế firmware (Embedded Firmware)
**Công việc (Tasks)**
- Lập trình firmware điều khiển đúng slot và xử lý lệnh hợp lệ.
- Thiết kế State Machine, trạng thái máy và quy trình xịt.
- Xử lý lệnh trùng, lỗi và phản hồi kết quả cho TP3.

**Đầu ra (Deliverables):** Mã nguồn firmware, sơ đồ trạng thái máy, mô tả luồng xử lý lệnh.

**Tiêu chí hoàn thành:** Firmware điều khiển đúng slot và phản hồi kết quả rõ ràng.

#### P3 — An toàn hệ thống (Safety Controls)
**Công việc (Tasks)**
- Quy định điều kiện cho phép xịt và dừng khẩn cấp.
- Khóa cơ cấu khi cửa mở, hết nước hoa, lỗi cảm biến hoặc lỗi nghiêm trọng.
- Quy định cách khôi phục máy an toàn sau sự cố.

**Đầu ra (Deliverables):** Bộ quy tắc an toàn, logic xử lý lỗi, danh sách tình huống khóa máy.

**Tiêu chí hoàn thành:** Máy không xịt khi điều kiện an toàn không được đáp ứng.

#### P4 — Cảm biến và hiệu chuẩn (Sensors & Spray Calibration)
**Công việc (Tasks)**
- Thiết kế cảm biến theo dõi trạng thái, lượng nước hoa và phát hiện lỗi.
- Xây dựng quy trình hiệu chuẩn lượng xịt và ghi nhận kết quả đo.

**Đầu ra (Deliverables):** Thiết kế cảm biến, quy trình hiệu chuẩn, bảng kết quả đo.

**Tiêu chí hoàn thành:** Cảm biến hoạt động và lượng xịt được đánh giá theo tiêu chí đã đặt.

#### P5 — Prototype và tích hợp (Prototype Integration)
**Công việc (Tasks)**
- Lắp ráp hoặc mô phỏng kiosk tối thiểu 4 slot.
- Tích hợp firmware, cảm biến, cơ cấu xịt và giao tiếp với TP3.

**Đầu ra (Deliverables):** Prototype 5 slot, sơ đồ tích hợp, kết quả chạy thử.

**Tiêu chí hoàn thành:** Prototype mô phỏng hoặc vận hành được các chức năng chính.

#### P6 — Kiểm thử và nghiệm thu (Testing & Acceptance)
**Công việc (Tasks)**
- Kiểm thử từng slot, cảm biến, trạng thái máy và liên động an toàn.
- Ghi nhận lỗi, sửa lỗi và kiểm thử lại.

**Đầu ra (Deliverables):** Bộ test case, kết quả kiểm thử, biên bản nghiệm thu.

**Tiêu chí hoàn thành:** Các chức năng và điều kiện an toàn đạt yêu cầu kiểm thử.

### 3. Thành phần chính
| Thành phần | Chức năng |
|---|---|
| Bộ điều khiển nhúng | Chạy firmware và điều khiển từng slot |
| 4 slot và cơ cấu xịt | Chứa nước hoa và thực hiện chu trình xịt theo lệnh |
| Cảm biến | Đo trạng thái cửa, lượng nước hoa và phát hiện bất thường |
| State Machine | Kiểm soát trạng thái và chuyển trạng thái hợp lệ |
| Safety Interlock | Chặn hoạt động khi có điều kiện không an toàn |
| Prototype | Minh họa và kiểm chứng chức năng trước tích hợp toàn hệ thống |

### 4. Quy tắc quan trọng
- Mỗi lệnh hợp lệ chỉ được phép dẫn đến tối đa một lần xịt thành công.
- Không xịt khi cửa mở, đang bảo trì, slot không đủ nước hoa hoặc có lỗi nghiêm trọng.
- Firmware phải từ chối lệnh trùng, hết hạn, sai máy hoặc sai slot.
- Chỉ kích hoạt slot được chỉ định; điều khiển độc lập không mặc nhiên có nghĩa cho phép 5 slot xịt đồng thời.
- Phân biệt `ACK` (đã nhận lệnh) với `SUCCESS` (đã xịt thành công).
- Ghi lại lỗi và kết quả xịt để TP3 truyền về hệ thống; không tự coi màn hình kiosk là bằng chứng thanh toán.

### 5. Đầu ra dự kiến
Hoàn thành bộ tài liệu và hiện vật P1–P6: sơ đồ phần cứng, BOM, firmware, State Machine, quy tắc an toàn, thiết kế cảm biến, quy trình/kết quả hiệu chuẩn, prototype và tích hợp , hướng dẫn tích hợp, báo cáo kiểm thử và checklist nghiệm thu. Tên file ở trên là **quy ước bàn giao đề xuất**, chưa phải các file con đã được tạo hoặc các chức năng đã triển khai.

### 6. Tiêu chí nghiệm thu đề xuất
- Có tối thiểu 5 slot có thể định danh, điều khiển và kiểm thử riêng biệt.
- Firmware xử lý đúng lệnh, trạng thái, phản hồi và các điều kiện an toàn.
- Có quy trình hiệu chuẩn và dữ liệu đo phù hợp với loại prototype (với mô phỏng LED chỉ kiểm tra logic, không xác nhận lượng xịt thực).
- Có báo cáo thử nghiệm, nhật ký lỗi, kiểm thử lại và tài liệu bàn giao.
