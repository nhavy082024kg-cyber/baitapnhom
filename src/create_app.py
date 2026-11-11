from flask import Flask

from api.middleware import setup_middleware
from api.routes import register_routes
from api.swagger import register_swagger
from app_logging import setup_logging
from config import FactoryConfig
from cors import setup_cors
from error_handler import register_error_handlers
from infrastructure.databases import init_db


def create_app() -> Flask:
    """Application factory. Order matters: config -> logging -> CORS -> database -> middleware -> routes."""
    app = Flask(__name__)
    app.config.from_object(FactoryConfig.get_config())

    setup_logging(app)
    setup_cors(app)
    init_db(app)
    setup_middleware(app)
    register_error_handlers(app)
    register_routes(app)
    register_swagger(app)
    return app
