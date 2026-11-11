from flask import request


def setup_cors(app):
    """Minimal CORS so the Figma/React front-end on another port can call the API."""
    allowed = app.config.get("CORS_ORIGINS", "*")

    @app.after_request
    def _cors(response):
        origin = request.headers.get("Origin")
        if origin and (allowed == "*" or origin in [o.strip() for o in allowed.split(",")]):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Vary"] = "Origin"
            response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, X-Device-Serial, X-Device-Secret"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        return response

    @app.route("/<path:_any>", methods=["OPTIONS"])
    def _preflight(_any):
        return "", 204
