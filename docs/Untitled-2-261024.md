Module quản lý cảm biến (SensorManager)
Mục đích
Lớp SensorManager chịu trách nhiệm quản lý toàn bộ các cảm biến của hệ thống ScentStation, bao gồm:

Cảm biến khối lượng HX711 để đo lượng nước hoa còn lại.
Cảm biến phát hiện rò rỉ dung dịch.
Cảm biến cửa để kiểm tra trạng thái đóng/mở của máy.
Cấu hình phần cứng
Thành phần	Chân kết nối
HX711 DOUT	GPIO 16
HX711 SCK	GPIO 4
Leak Sensor	GPIO 36
Door Sensor	GPIO 18
Solenoid Valve	GPIO 23
Định nghĩa trạng thái hệ thống
enum class SystemState
{
    NORMAL,
    MAINTENANCE,
    ERROR_LEAK,
    ERROR_DOOR
};
Ý nghĩa:

NORMAL: Hoạt động bình thường.
MAINTENANCE: Chế độ bảo trì.
ERROR_LEAK: Phát hiện rò rỉ.
ERROR_DOOR: Cửa đang mở.
Khởi tạo cảm biến
void begin()
{
    pinMode(Pinout::LEAK_SENSOR, INPUT);
    pinMode(Pinout::DOOR_SENSOR, INPUT_PULLUP);

    scale.begin(
        Pinout::HX711_DOUT,
        Pinout::HX711_SCK
    );

    scale.set_scale(Config::CALIB_FACTOR);
    scale.tare();
}
Chức năng:

Khởi tạo các chân GPIO.
Kết nối module HX711.
Nạp hệ số hiệu chuẩn cho Load Cell.
Đặt giá trị cân ban đầu về 0.
Đọc khối lượng nước hoa
float getWeight()
{
    return scale.is_ready()
           ? scale.get_units(5)
           : -1.0f;
}
Nguyên lý:

Kiểm tra HX711 có sẵn sàng hay không.
Lấy trung bình 5 lần đo để giảm nhiễu.
Nếu cảm biến lỗi sẽ trả về -1.0f.
Kiểm tra an toàn
SystemState checkSafety(bool isMaintenance)
{
    if (
        analogRead(Pinout::LEAK_SENSOR)
        > Config::LEAK_THRESHOLD
    )
    {
        return SystemState::ERROR_LEAK;
    }

    if (
        digitalRead(Pinout::DOOR_SENSOR) == HIGH
        && !isMaintenance
    )
    {
        return SystemState::ERROR_DOOR;
    }

    return SystemState::NORMAL;
}
Chức năng:

Đọc cảm biến rò rỉ.
So sánh với ngưỡng an toàn.
Kiểm tra trạng thái cửa máy.
Trả về trạng thái hiện tại của hệ thống.
Luồng hoạt động
Khởi tạo hệ thống
        │
        ▼
 Đọc cảm biến rò rỉ
        │
        ├── Có lỗi ──► ERROR_LEAK
        │
        ▼
   Kiểm tra cửa
        │
        ├── Cửa mở ──► ERROR_DOOR
        │
        ▼
      NORMAL
Vai trò trong hệ thống ScentStation
Module SensorManager là lớp bảo vệ đầu tiên của hệ thống. Trước khi thực hiện thao tác xịt nước hoa, hệ thống phải:

Kiểm tra có rò rỉ dung dịch hay không.
Kiểm tra cửa máy có đang mở hay không.
Đảm bảo cảm biến cân hoạt động bình thường.
Cho phép bộ điều khiển đầu phun thực hiện thao tác xịt khi tất cả điều kiện an toàn đều đạt yêu cầu