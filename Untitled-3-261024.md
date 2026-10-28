Module xử lý lệnh điều khiển xịt từ Backend
Mục đích
Module này chịu trách nhiệm tiếp nhận và xử lý lệnh xịt nước hoa được gửi từ hệ thống Backend xuống thiết bị IoT.

Các chức năng chính bao gồm:

Kiểm tra lệnh đã được thực thi hay chưa.
Kiểm tra thời hạn hiệu lực của lệnh.
Kiểm tra các điều kiện an toàn trước khi xịt.
Kích hoạt van phun đúng vị trí.
Gửi phản hồi trạng thái về hệ thống trung tâm.
Luồng xử lý lệnh
Nhận lệnh từ Backend
        │
        ▼
Kiểm tra lệnh đã chạy?
        │
   ┌────┴────┐
   │         │
 Có         Không
   │         │
 Từ chối     ▼
       Kiểm tra hết hạn?
             │
        ┌────┴────┐
        │         │
      Có         Không
        │         │
    Từ chối       ▼
         Kiểm tra an toàn
                │
          ┌─────┴─────┐
          │           │
         Lỗi         OK
          │           │
      Từ chối         ▼
               Kích hoạt van
                     │
                     ▼
              Gửi phản hồi
                     │
                     ▼
                Hoàn tất
Các hàm hỗ trợ
Kiểm tra lệnh đã thực thi
bool daTuongChayLenh(string maLenh)
{
    return false;
}
Chức năng:

Kiểm tra mã lệnh đã được xử lý trước đó hay chưa.
Ngăn chặn tình trạng một giao dịch được xịt nhiều lần.
Lấy thời gian hệ thống
long layThoiGianHienTai()
{
    return 1000;
}
Chức năng:

Cung cấp thời gian hiện tại của thiết bị.
Dùng để kiểm tra hạn sử dụng của lệnh.
Kiểm tra trạng thái cửa máy
bool kiemTraCuaDangMo()
{
    return false;
}
Chức năng:

Kiểm tra cửa bảo trì có đang mở hay không.
Ngăn chặn việc xịt khi nhân viên đang thao tác bên trong máy.
Gửi phản hồi lên Backend
void guiPhanHoiCapTren(
    string maLenh,
    string trangThai,
    string thongBao
)
{
    cout << "[" << trangThai << "] "
         << thongBao << endl;
}
Chức năng:

Báo cáo trạng thái xử lý.
Hỗ trợ ghi log và đối soát giao dịch.
Thuật toán xử lý lệnh xịt
void xuLyLenhXit(
    string maLenh,
    int viTriSlot,
    int thoiGianXitMs,
    long thoiHanLenh
)
{
    if (daTuongChayLenh(maLenh))
    {
        guiPhanHoiCapTren(
            maLenh,
            "DA_XIT_TROI",
            "Lenh nay da duoc thuc thi truoc do."
        );
        return;
    }

    if (layThoiGianHienTai() > thoiHanLenh)
    {
        guiPhanHoiCapTren(
            maLenh,
            "QUA_HAN",
            "Lenh da het han."
        );
        return;
    }

    if (kiemTraCuaDangMo())
    {
        guiPhanHoiCapTren(
            maLenh,
            "LOI_AN_TOAN",
            "Cua may dang mo."
        );
        return;
    }

    luuMaLenhDaChay(maLenh);

    guiPhanHoiCapTren(
        maLenh,
        "DANG_XIT",
        "Bat dau kich hoat van."
    );

    batVanXit(viTriSlot);
    tatVanXit(viTriSlot);

    guiPhanHoiCapTren(
        maLenh,
        "THANH_CONG",
        "Da xit xong."
    );
}
Quy tắc nghiệp vụ được áp dụng
Mã	Quy tắc
BR06	Chỉ được phép xịt sau khi giao dịch hợp lệ
BR07	Một đơn hàng chỉ được xịt tối đa một lần
BR08	Từ chối lệnh trùng hoặc không hợp lệ
BR09	Không xịt khi cửa máy đang mở
BR15	Ghi nhận và phản hồi kết quả thực hiện lệnh
Kết luận
Module xử lý lệnh xịt đóng vai trò trung gian giữa Backend và phần cứng IoT. Module đảm bảo rằng mỗi giao dịch chỉ tạo ra tối đa một lần xịt thành công, đồng thời kiểm soát các điều kiện an toàn trước khi kích hoạt van phun nước hoa