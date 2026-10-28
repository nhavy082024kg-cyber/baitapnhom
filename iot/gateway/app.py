# MỤC ĐÍCH: tạo ứng dụng Flask cho phần P1 và chạy độc lập.
#   create_app(cfg, clock)  -> Flask app (clock chỉ dùng khi test để giả lập thời gian)
#   Chạy thử:  python -m gateway.app     (mặc định http://127.0.0.1:5001)
#   Bắt buộc đặt SS_GATEWAY_SECRET và SS_ADMIN_TOKEN, nếu không các endpoint tương ứng trả 401.
# Khi ghép vào dự án chung của nhóm: chỉ cần app.register_blueprint(gateway.api.bp) và gọi init_schema().
import logging
import os
import time

from flask import Flask, g, jsonify
from werkzeug.exceptions import HTTPException

from .api import bp, register_errors
from .config import Config
from .db import init_schema


def create_app(cfg: Config | None = None, clock=None) -> Flask:
    cfg = cfg or Config()
    app = Flask(__name__)
    app.config["CFG"] = cfg
    app.config["CLOCK"] = clock or (lambda: int(time.time()))
    init_schema(cfg.db_path)
    app.register_blueprint(bp)
    register_errors(app)

    @app.errorhandler(HTTPException)
    def on_http(e):
        return jsonify({"error": e.name.lower().replace(" ", "_"), "message": e.description}), e.code

    @app.errorhandler(Exception)
    def on_unexpected(e):
        logging.exception("lỗi không lường trước")
        return jsonify({"error": "internal_error", "message": "Lỗi máy chủ"}), 500

    @app.teardown_appcontext
    def close_db(_):
        d = g.pop("db", None)
        if d is not None:
            d.close()                 # phần chưa commit sẽ bị hủy

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    return app


if __name__ == "__main__":      # pragma: no cover
    logging.basicConfig(level=logging.INFO)
    create_app().run(host="127.0.0.1", port=int(os.environ.get("PORT", "5001")))
