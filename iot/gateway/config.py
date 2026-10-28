# MỤC ĐÍCH: gom các cấu hình của gateway vào một chỗ, đọc từ biến môi trường.
#   SS_DB_PATH         : đường dẫn file SQLite (mặc định gateway.db)
#   SS_GATEWAY_SECRET  : bí mật chung giữa broker MQTT và gateway (header X-Gateway-Secret)
#   SS_ADMIN_TOKEN     : token tạm cho các API quản trị (đăng ký máy, thu hồi...).
#                        Khi ghép với phần đăng nhập/phân quyền của Task 1 thì thay bằng JWT + RBAC.
import os
from dataclasses import dataclass, field


@dataclass
class Config:
    db_path: str = field(default_factory=lambda: os.environ.get("SS_DB_PATH", "gateway.db"))
    gateway_secret: str = field(default_factory=lambda: os.environ.get("SS_GATEWAY_SECRET", ""))
    admin_token: str = field(default_factory=lambda: os.environ.get("SS_ADMIN_TOKEN", ""))
    max_payload_bytes: int = 16 * 1024      # tin nhắn lớn hơn mức này bị từ chối (chống làm nghẽn)
