import re

from flask import jsonify

SWAGGER_HTML = """<!doctype html>
<html><head><meta charset="utf-8"><title>ScentStation API</title>
<link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5.17.14/swagger-ui.css"></head>
<body><div id="ui"></div>
<script src="https://unpkg.com/swagger-ui-dist@5.17.14/swagger-ui-bundle.js"></script>
<script>SwaggerUIBundle({url: "/openapi.json", dom_id: "#ui"});</script></body></html>"""

_TYPES = {"Str": "string", "String": "string", "Email": "string", "Int": "integer", "Integer": "integer",
          "Bool": "boolean", "Boolean": "boolean", "Float": "number", "Decimal": "number", "Date": "string",
          "DateTime": "string", "List": "array", "Dict": "object", "Nested": "object"}


def _body_schema(schema_cls) -> dict:
    """Marshmallow schema -> small JSON-schema (the same class that validates the request)."""
    schema = schema_cls()
    properties, required = {}, []
    for name, field in schema.fields.items():
        properties[name] = {"type": _TYPES.get(type(field).__name__, "string")}
        if field.required:
            required.append(name)
    return {"type": "object", "properties": properties, "required": required}


def build_openapi(app) -> dict:
    """Generated from the real routes: the docs can never drift away from the code."""
    paths = {}
    for rule in app.url_map.iter_rules():
        if rule.endpoint == "static" or rule.rule.startswith(("/docs", "/openapi")) or "OPTIONS" == rule.rule:
            continue
        view = app.view_functions[rule.endpoint]
        if rule.endpoint.startswith("_") or view.__name__.startswith("_preflight"):
            continue
        doc = (view.__doc__ or "").strip().splitlines()
        path = re.sub(r"<(?:[^:>]+:)?([^>]+)>", r"{\1}", rule.rule)
        for method in sorted(rule.methods - {"HEAD", "OPTIONS"}):
            operation = {"tags": [rule.endpoint.split(".")[0]], "summary": doc[0] if doc else view.__name__,
                         "description": "\n".join(l.strip() for l in doc[1:]),
                         "parameters": [{"name": a, "in": "path", "required": True, "schema": {"type": "string"}}
                                        for a in sorted(rule.arguments)],
                         "responses": {"200": {"description": "OK"}}}
            auth = getattr(view, "requires_auth", None)
            if auth == "bearer":
                operation["security"] = [{"bearerAuth": []}]
            elif auth == "device":
                operation["security"] = [{"deviceSerial": [], "deviceSecret": []}]
            schema_cls = getattr(view, "request_schema", None)
            if schema_cls and method in ("POST", "PUT", "PATCH"):
                operation["requestBody"] = {"required": True, "content": {"application/json": {
                    "schema": _body_schema(schema_cls)}}}
            paths.setdefault(path, {})[method.lower()] = operation
    return {
        "openapi": "3.0.3",
        "info": {"title": "ScentStation API", "version": "1.0.0",
                 "description": "Multi-brand IoT perfume experience platform"},
        "paths": paths,
        "components": {"securitySchemes": {
            "bearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"},
            "deviceSerial": {"type": "apiKey", "in": "header", "name": "X-Device-Serial"},
            "deviceSecret": {"type": "apiKey", "in": "header", "name": "X-Device-Secret"}}},
    }


def register_swagger(app):
    @app.route("/openapi.json")
    def openapi_json():
        """OpenAPI document generated from the routes."""
        return jsonify(build_openapi(app))

    @app.route("/docs")
    def swagger_ui():
        """Swagger UI (open http://localhost:9999/docs)."""
        return SWAGGER_HTML
