# MỤC ĐÍCH: mô tả cấu trúc JSON hợp lệ của 4 loại tin nhắn từ máy gửi lên, dùng pydantic để kiểm tra kiểu và giới hạn.
#   TelemetryT : trạng thái máy gửi mỗi 30 giây (cũng là heartbeat)       -> P3 xử lý
#   EventT     : sự kiện có id duy nhất (STARTUP, SENSOR_ERROR...)        -> P1 lưu, chống trùng
#   AckT       : máy báo đã nhận/từ chối lệnh                             -> P4 xử lý
#   ResultT    : kết quả thực thi lệnh phun (OK / FAILED / UNCERTAIN)     -> P4 xử lý
# Trường lạ trong JSON bị bỏ qua (extra="ignore"); trường sai kiểu hoặc ngoài giới hạn làm tin bị từ chối (BAD_PAYLOAD).
from pydantic import BaseModel, ConfigDict, Field


class SlotT(BaseModel):
    model_config = ConfigDict(extra="ignore")
    weight_mg: int | None = Field(default=None, ge=-1, le=10_000_000)    # khối lượng chai (mg), -1 = không đọc được
    remaining: int | None = Field(default=None, ge=-1, le=1_000_000)     # số lần phun còn lại ước tính
    sales: int = Field(default=0, ge=0, le=100_000_000)                  # số lần phun bán
    diag: int = Field(default=0, ge=0, le=100_000_000)                   # số lần phun thử
    flags: int = Field(default=0, ge=0, le=255)                          # cờ LOW/EMPTY/LEAK/DIVERGENT/SENSOR


class TelemetryT(BaseModel):
    model_config = ConfigDict(extra="ignore")
    mode: str = Field(pattern="^(IDLE|DISPENSING|MAINTENANCE|FAULT)$")
    fault: str = Field(default="", max_length=64)
    door: bool = False
    leak: bool = False
    power: str | None = Field(default=None, max_length=32)
    fw: str | None = Field(default=None, max_length=32)                  # phiên bản firmware
    cfg: str | None = Field(default=None, max_length=32)                 # phiên bản cấu hình
    slots: list[SlotT] = Field(default_factory=list, max_length=8)


class EventT(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(min_length=1, max_length=96)
    type: str = Field(min_length=1, max_length=48)
    detail: str = Field(default="", max_length=400)


class AckT(BaseModel):
    model_config = ConfigDict(extra="ignore")
    command_id: str = Field(min_length=1, max_length=64)
    accepted: bool
    code: str = Field(default="", max_length=64)


class ResultT(BaseModel):
    model_config = ConfigDict(extra="ignore")
    command_id: str = Field(min_length=1, max_length=64)
    order_id: str = Field(default="", max_length=64)
    outcome: str = Field(pattern="^(OK|FAILED|UNCERTAIN)$")
    code: str = Field(default="", max_length=64)
    delta_mg: int = Field(default=0, ge=-10_000_000, le=10_000_000)
    executed_ms: int = Field(default=0, ge=0, le=3_600_000)
    diagnostic: bool = False


MODELS = {"telemetry": TelemetryT, "event": EventT, "ack": AckT, "result": ResultT}
