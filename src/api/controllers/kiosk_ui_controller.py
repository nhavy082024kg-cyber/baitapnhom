import os

from flask import Blueprint, send_from_directory

KIOSK_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "static", "kiosk")

kiosk_ui_bp = Blueprint("kiosk_ui", __name__)


@kiosk_ui_bp.route("/kiosk")
@kiosk_ui_bp.route("/kiosk/")
def kiosk_app():
    """Touch-screen kiosk web app (open http://localhost:9999/kiosk/?serial=...&secret=...). No login: uses device credentials."""
    response = send_from_directory(KIOSK_DIR, "index.html")
    response.headers["Cache-Control"] = "no-store"
    return response
