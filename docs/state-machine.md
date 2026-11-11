# State machines và luồng nghiệp vụ

Nguồn sự thật trong code: `src/domain/models/order_state_machine.py`, `src/domain/models/dispense_policy.py`, `src/domain/constants.py`.
Mọi thay đổi `order.status` **chỉ** đi qua `OrderWorkflow` và `assert_transition()`.

## 1. Trạng thái đơn hàng

```mermaid
stateDiagram-v2
    [*] --> CREATED
    CREATED --> AWAITING_PAYMENT
    CREATED --> CANCELLED
    AWAITING_PAYMENT --> PAID: webhook hợp lệ
    AWAITING_PAYMENT --> EXPIRED: quá hạn
    AWAITING_PAYMENT --> CANCELLED
    PAID --> DISPENSING: tạo lệnh xịt
    PAID --> MANUAL_REVIEW: máy không còn xịt được
    DISPENSING --> DISPENSED: máy báo EXECUTED
    DISPENSING --> DISPENSE_FAILED: máy báo FAILED/REJECTED
    DISPENSING --> UNCERTAIN: quá hạn không có kết quả
    DISPENSE_FAILED --> MANUAL_REVIEW
    DISPENSE_FAILED --> REFUNDED
    UNCERTAIN --> MANUAL_REVIEW
    UNCERTAIN --> REFUNDED
    MANUAL_REVIEW --> REFUNDED
    MANUAL_REVIEW --> DISPENSED: xác nhận thủ công đã xịt
    EXPIRED --> MANUAL_REVIEW: tiền về muộn
    CANCELLED --> MANUAL_REVIEW: tiền về muộn
    DISPENSED --> [*]
    REFUNDED --> [*]
```

Hai trạng thái cuối: `DISPENSED`, `REFUNDED`. Không có cạnh nào từ lỗi/không chắc chắn quay về `DISPENSING` ⇒ **không bao giờ tự xịt lần hai**.

## 2. Trạng thái lệnh xịt (`dispense_commands`)

```mermaid
stateDiagram-v2
    [*] --> CREATED
    CREATED --> SENT: thiết bị lấy lệnh
    SENT --> ACKED: thiết bị ack
    ACKED --> EXECUTED
    ACKED --> FAILED
    SENT --> REJECTED: chữ ký/hạn/serial/trùng sai
    CREATED --> TIMEOUT
    SENT --> TIMEOUT
    ACKED --> TIMEOUT
```

Ràng buộc: `UNIQUE(order_id, type)` ⇒ một đơn có tối đa một lệnh SALE. Chữ ký HMAC trên `command_id|serial|slot|type|expires_at`.

## 3. Chuỗi xử lý thanh toán → xịt (sequence)

```mermaid
sequenceDiagram
    participant K as Kiosk UI
    participant B as Backend
    participant P as Payment Provider
    participant D as Thiết bị (simulator)
    K->>B: POST /kiosk/orders {slot}
    B-->>K: order_code, QR, expires_at
    K->>P: khách quét QR và trả tiền
    P->>B: POST /webhooks/payment (X-Signature)
    B->>B: verify chữ ký, tiền, tiền tệ, event_id chưa xử lý
    B->>B: order PAID -> tạo 1 lệnh SALE (đã ký) -> DISPENSING
    D->>B: GET /device/commands
    D->>B: POST /commands/{id}/ack
    D->>D: kiểm tra chữ ký, hạn, cửa, slot rồi xịt 1 lần
    D->>B: POST /commands/{id}/result EXECUTED
    B->>B: order DISPENSED, trừ tồn, ghi audit
    K->>B: GET /kiosk/orders/{code} (poll)
    B-->>K: DISPENSED
```

## 4. Các trạng thái khác

| Đối tượng | Giá trị | Ghi chú |
|---|---|---|
| Máy (kết nối) | ONLINE / UNSTABLE / OFFLINE | Tính từ heartbeat cuối so với `HEARTBEAT_ONLINE_SECONDS` |
| Máy (chế độ) | NORMAL / MAINTENANCE / DISABLED | MAINTENANCE → NORMAL cần `post_test_passed` |
| Slot | AVAILABLE / LOW / EMPTY / DISABLED / ERROR | Dẫn xuất từ tồn ước tính và ngưỡng thấp |
| Chai | AVAILABLE / INSTALLED / NEARLY_EMPTY / EMPTY / DAMAGED / EXPIRED | |
| Cảnh báo | OPEN → ACKNOWLEDGED → ASSIGNED → RESOLVED ⇄ REOPENED | Chống trùng bằng `dedup_key` |
| Thanh toán | WAITING / SUCCESS / FAILED / CANCELLED / EXPIRED | |
| Hoàn tiền | REQUESTED / APPROVED / COMPLETED / REJECTED | |

## 5. Khi nào kiosk được bán (policy)

Đơn chỉ được tạo khi **tất cả** đúng: tenant ACTIVE · máy ONLINE · chế độ NORMAL · cửa đóng · không có lỗi nghiêm trọng · slot AVAILABLE/LOW và còn đủ nước hoa cho một lần xịt · slot có sản phẩm và giá. Sai một điều kiện ⇒ từ chối tạo đơn với thông báo rõ ràng (`assert_can_accept_order`).

## 6. Bảng kịch bản lỗi và kết quả mong đợi

| # | Tình huống | Hệ thống làm gì |
|---|---|---|
| 1 | Webhook gửi hai lần | Lần 2 trả `duplicate_ignored`, không tạo lệnh thứ hai |
| 2 | Sai chữ ký | 401, không đổi trạng thái |
| 3 | Số tiền/tiền tệ không khớp | 422, đơn giữ AWAITING_PAYMENT |
| 4 | Trả tiền sau khi đơn hết hạn | Đơn → MANUAL_REVIEW (không xịt) |
| 5 | Máy mở cửa lúc có lệnh | Thiết bị REJECTED/FAILED → DISPENSE_FAILED → MANUAL_REVIEW |
| 6 | Máy không báo kết quả | Job quá hạn → UNCERTAIN → MANUAL_REVIEW, không tự thử lại |
| 7 | Hoàn tiền khi chưa step-up | 403 |
| 8 | Brand B đọc dữ liệu brand A | 404 |
| 9 | Máy bị thu hồi gọi API | 401 |
