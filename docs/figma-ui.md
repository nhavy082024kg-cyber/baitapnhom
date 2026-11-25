# Đặc tả UI cho Figma

Mình không thao tác trực tiếp trong Figma được, nên file này là **bản giao việc cho bạn dựng**: khung (frame), màn hình, thành phần, trạng thái và API mà từng màn hình gọi. Dựng theo thứ tự ưu tiên ở mục 7.

## 1. Link Figma
https://www.figma.com/proto/4oBf2AuukackKOwgB4XA3Z/ScentStation-UI?node-id=4-2&t=iqPEPfEjn7wdbjzu-0&scaling=min-zoom&content-scaling=fixed&page-id=0%3A1&starting-point-node-id=4%3A2&show-proto-sidebar=1
```
## 2. Design tokens đề xuất (phong cách nước hoa: sang, tối giản)

| Token | Giá trị | Dùng cho |
|---|---|---|
| `color/ink` | `#1C1A1F` | chữ chính, nền kiosk tối |
| `color/paper` | `#FAF7F2` | nền portal, nền thẻ |
| `color/gold` | `#B08D57` | nút chính, điểm nhấn |
| `color/muted` | `#6E6A73` | chữ phụ |
| `color/success` | `#2F7D5B` | DISPENSED, ONLINE |
| `color/warning` | `#C98A1B` | LOW, UNSTABLE, MANUAL_REVIEW |
| `color/danger` | `#B3382C` | lỗi, OFFLINE, CRITICAL |
| Chữ tiêu đề | Playfair Display / Cormorant, 32–56 | tên nước hoa, tiêu đề kiosk |
| Chữ nội dung | Inter, 14–20 (portal), 22–32 (kiosk) | còn lại |
| Lưới | 8px; kiosk lề 48px; portal 12 cột | |
| Bo góc | 12px thẻ, 999px nút kiosk | |
| Vùng chạm kiosk | tối thiểu 72×72px | cảm ứng |

Trạng thái luôn dùng **màu + biểu tượng + chữ** (không chỉ màu) để đảm bảo accessibility.

## 3. Component cần tạo (Variants trong Figma)

| Component | Variants |
|---|---|
| Button | primary / secondary / danger × default / hover / disabled / loading |
| StatusBadge | ONLINE, UNSTABLE, OFFLINE, MAINTENANCE, DISABLED, ERROR; AVAILABLE, LOW, EMPTY; mọi `OrderStatus` |
| SeverityTag | INFO, WARNING, CRITICAL |
| PerfumeCard (kiosk) | available / low / sold-out (mờ + nhãn "Tạm hết") |
| SlotTile (portal) | có chai (tên + thanh tồn %) / trống / tắt |
| StockBar | >50% / 20–50% / <20% |
| DataTable | có lọc, sắp xếp, phân trang, trạng thái rỗng, đang tải, lỗi |
| Modal xác nhận | thường / **step-up** (ô mật khẩu) |
| Toast | success / error |
| EmptyState, Skeleton | cho mọi bảng |

## 4. Màn hình KIOSK (1080×1920) – dùng API thiết bị

| # | Màn hình | Nội dung | API |
|---|---|---|---|
| K1 | Home / Attract | Logo brand, video/ảnh, nút "Chạm để trải nghiệm"; tự quay về sau 60s không thao tác | `GET /kiosk/catalog` |
| K2 | Chọn nước hoa | Lưới 2×2 (4 slot) PerfumeCard: ảnh, tên, giá/xịt; slot hết thì mờ | `GET /kiosk/catalog` |
| K3 | Chi tiết nước hoa | Ảnh lớn, notes (top/middle/base), mô tả, hướng dẫn dùng, giá, nút "Trải nghiệm"; QR sản phẩm nhỏ góc dưới | `product_qr_url` |
| K4 | Xác nhận | Tên, giá, tiền tệ; "Xác nhận và tạo mã QR"; nút Quay lại | `POST /kiosk/orders` |
| K5 | Thanh toán QR | QR lớn, đếm ngược `expires_at`, trạng thái "Đang chờ thanh toán"; nút Hủy | poll `GET /kiosk/orders/{code}` mỗi 2s |
| K6 | Hết hạn / hủy / lỗi thanh toán | Thông báo + nút "Thử lại" | cùng API |
| K7 | Chuẩn bị xịt | Hình minh họa đặt tay/que thử vào khay, "Sẽ xịt sau 3 giây" | trạng thái `DISPENSING` |
| K8 | Thành công | "Cảm ơn!", QR xem thêm/ khuyến mãi, tự về Home sau 15s | `DISPENSED` |
| K9 | Đã thanh toán nhưng xịt lỗi | Giải thích rõ, **mã đơn** lớn, hướng dẫn liên hệ nhân viên; không có nút thử lại | `MANUAL_REVIEW`/`DISPENSE_FAILED`/`UNCERTAIN`, dùng `message` |
| K10 | Tạm ngưng phục vụ | Khi `orderable=false` (bảo trì, offline, cửa mở): thông báo thân thiện, không cho chọn | `reason` |

Quy tắc UX kiosk: chữ ≥ 24px, tương phản cao, mỗi màn một hành động chính, luôn có nút quay lại trừ K7, K8, timeout tự về K1.

## 5. Màn hình WEB PORTAL (1440×1024)

Bố cục chung: sidebar trái (menu theo quyền từ `/auth/me`), header (brand, người dùng, chuông cảnh báo), vùng nội dung.

| # | Màn hình | Role chính | Thành phần | API |
|---|---|---|---|---|
| W1 | Đăng nhập | tất cả | email, mật khẩu, thông báo khóa tài khoản | `POST /auth/login` |
| W2 | Tổng quan (dashboard) | Ops, Admin | thẻ số máy theo trạng thái, đơn hôm nay, hàng đợi review, cảnh báo mở | `/machines`, `/orders`, `/alerts` *(biểu đồ doanh thu: chờ API báo cáo)* |
| W3 | Danh sách brand | Super Admin | bảng, tạo brand, suspend/activate | `/tenants` |
| W4 | Người dùng | Super/Brand Admin | bảng, tạo user + chọn role, khóa/mở | `/users` |
| W5 | Sản phẩm | Brand Admin | bảng + form (notes, giá, ảnh, QR) | `/products` |
| W6 | Địa điểm | Brand Admin | bảng + form | `/locations` |
| W7 | Danh sách máy | Ops, Admin | bảng: trạng thái kết nối, lần cuối online, firmware | `GET /machines` |
| W8 | Chi tiết máy | Ops, Tech, Admin | 4 SlotTile (sản phẩm, StockBar, giá), nút Bật/Tắt máy, Bảo trì, Test spray (modal step-up), tab: Sự kiện, Lịch sử | `GET /machines/{id}`, `PATCH mode`, `POST test-spray` |
| W9 | Cấu hình slot | Brand Admin | drawer: sản phẩm, giá, liều xịt, ml/xịt, ngưỡng thấp, bật/tắt | `PUT /slots/{id}` |
| W10 | Đăng ký máy | Brand Admin | form + màn **hiển thị device_secret một lần** (nút copy, cảnh báo "không xem lại được") | `POST /machines` |
| W11 | Kho: lô và chai | Inventory | 2 tab Lô/Chai, lọc trạng thái, form nhập lô, đăng ký chai | `/inventory/*` |
| W12 | Lắp/thay chai | Inventory | chọn slot → quét/nhập mã chai → nhập cân nặng trước/sau → xác nhận (cảnh báo nếu sai nước hoa) | `install-bottle` |
| W13 | Đơn hàng | Ops, Viewer | bảng lọc theo trạng thái/máy; chi tiết có **timeline** trạng thái | `GET /orders`, `/orders/{id}` |
| W14 | Hàng đợi review | Ops | danh sách đơn đã trả tiền chưa xịt; chi tiết chứng cứ; nút Hoàn tiền (modal step-up + lý do) | `?review_queue=true`, `POST refund` |
| W15 | Cảnh báo | Ops, Tech | bảng severity/trạng thái; Nhận việc, Đóng (ghi chú) | `/alerts` |
| W16 | Audit log | Admin | bảng + lọc hành động, mã đơn | `/audit-logs` |
| W17 | Bảo trì | Ops, Tech | danh sách ticket (lọc trạng thái/máy), chi tiết: checklist tick được, form kết quả (chẩn đoán, hành động, linh kiện, chi phí, ảnh), nút Test sau bảo trì, nút Đóng (vô hiệu hóa kèm lý do nếu chưa đủ điều kiện) | `/maintenance/tickets*` |
| W18 | Báo cáo | Admin, Ops | bộ lọc ngày, biểu đồ doanh thu theo ngày, top nước hoa, tỷ lệ xịt thành công, nút Tải CSV (giao dịch, tồn kho) | `/reports/dashboard`, `/reports/*.csv` |
| W19 | Khuyến mãi | Brand Admin | danh sách + form giá tạm thời (phạm vi sản phẩm/máy/địa điểm, thời gian), nút Kích hoạt / Kết thúc | `/promotions*` |
| W20 | Điều chỉnh kho | Inventory, Brand Admin | modal step-up + số ml còn lại + lý do bắt buộc | `POST /inventory/bottles/{id}/adjust` |
| W21 | Đối soát thanh toán | Ops, Brand Admin | dán/tải bản sao kê nhà cung cấp, kết quả 4 nhóm (khớp, lệch, thiếu nội bộ, thiếu ở nhà cung cấp) | `POST /reports/reconciliation` |
| W22 | Tổng quan nền tảng | Super Admin | số brand, máy, doanh thu toàn nền tảng | `GET /reports/platform` |

## 6. Prototype flows cần nối dây

1. **Mua hàng thành công**: K1 → K2 → K3 → K4 → K5 → K7 → K8 → K1
2. **Quá hạn thanh toán**: K5 → K6 → K2
3. **Trả tiền nhưng xịt lỗi**: K5 → K7 → K9
4. **Máy tạm ngưng**: K1 → K10
5. **Onboarding brand**: W1 → W3 → W4 → W5 → W10 → W9 → W11 → W12
6. **Xử lý đơn lỗi và hoàn tiền**: W2 → W14 → modal step-up → W14 (đơn REFUNDED)
7. **Bảo trì máy**: W15 → W8 → Bảo trì → Test spray → Trả máy NORMAL

