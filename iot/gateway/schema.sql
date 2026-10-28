-- MỤC ĐÍCH: các bảng mà RIÊNG phần P1 cần để chạy độc lập.
--   tenants            : brand (Dior, Gucci, Chanel, YSL, Hermès). Bản tối thiểu để P1 chạy một mình;
--                        khi ghép với Task 1 của nhóm thì dùng bảng tenants của Task 1.
--   machines           : máy kiosk đã đăng ký (mỗi máy thuộc đúng 1 brand).
--   device_credentials : mật khẩu MQTT (lưu băm) + khóa ký lệnh của từng máy.
--   device_events      : nhật ký sự kiện thiết bị; UNIQUE(machine_id, event_id) giúp chống lưu trùng.
--   gateway_audit      : nhật ký các tin nhắn bị từ chối và thao tác quản trị.
-- Thời gian lưu dạng số nguyên (giây Unix) cho đơn giản.
-- Các cột trạng thái chi tiết của máy (mode, door, leak...) do P3 thêm sau.
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS tenants (
  id         TEXT PRIMARY KEY,
  code       TEXT NOT NULL UNIQUE,                         -- dior, gucci, chanel, ysl, hermes (dùng trong topic MQTT)
  name       TEXT NOT NULL,
  status     TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','suspended')),   -- chữ thường, giống bảng tenants của nhóm
  created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS machines (
  id           TEXT PRIMARY KEY,
  tenant_id    TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  device_id    TEXT NOT NULL UNIQUE,                       -- số serial = client id MQTT = đoạn giữa của topic
  name         TEXT NOT NULL,
  location     TEXT,
  status       TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','disabled','revoked')),
  slot_count   INTEGER NOT NULL DEFAULT 5 CHECK (slot_count BETWEEN 1 AND 8),
  last_seen_at INTEGER,                                    -- lần cuối nhận được tin hợp lệ
  last_boot_at INTEGER,                                    -- lần cuối nhận sự kiện STARTUP
  created_at   INTEGER NOT NULL,
  updated_at   INTEGER NOT NULL,
  UNIQUE (tenant_id, id)
);
CREATE INDEX IF NOT EXISTS machines_tenant_idx ON machines (tenant_id);

CREATE TABLE IF NOT EXISTS device_credentials (
  machine_id       TEXT PRIMARY KEY REFERENCES machines(id) ON DELETE CASCADE,
  tenant_id        TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  mqtt_secret_hash TEXT NOT NULL,                          -- băm SHA-256 của mật khẩu MQTT (không lưu bản gốc)
  command_key_hex  TEXT NOT NULL,                          -- khóa HMAC dùng ký lệnh (P4 sẽ dùng)
  revoked_at       INTEGER,
  created_at       INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS device_events (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id   TEXT NOT NULL,
  machine_id  TEXT NOT NULL REFERENCES machines(id) ON DELETE CASCADE,
  event_id    TEXT NOT NULL,                               -- id duy nhất do thiết bị tạo
  type        TEXT NOT NULL,
  detail      TEXT NOT NULL DEFAULT '',
  received_at INTEGER NOT NULL,
  UNIQUE (machine_id, event_id)                            -- nhận lặp sau khi nối lại mạng chỉ lưu 1 lần
);

CREATE TABLE IF NOT EXISTS gateway_audit (
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  ts        INTEGER NOT NULL,
  action    TEXT NOT NULL,                                 -- DEVICE_MESSAGE_REJECTED, MACHINE_REGISTERED, MACHINE_REVOKED, ...
  tenant_id TEXT,
  device_id TEXT,
  detail    TEXT
);
