# MỤC ĐÍCH: mở kết nối SQLite và tạo bảng từ schema.sql.
#   connect(path)      -> kết nối có row_factory = sqlite3.Row (truy cập cột theo tên) và bật khóa ngoại.
#   init_schema(path)  -> chạy schema.sql (an toàn khi chạy lại nhiều lần nhờ IF NOT EXISTS).
import sqlite3
from pathlib import Path

SCHEMA = Path(__file__).resolve().parent / "schema.sql"


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(path: str) -> None:
    conn = connect(path)
    conn.executescript(SCHEMA.read_text(encoding="utf-8"))
    conn.commit()
    conn.close()
