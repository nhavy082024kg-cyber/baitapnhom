import os

try:
    from dotenv import load_dotenv

    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    load_dotenv(os.path.join(BASE_DIR, ".env"))

except ImportError:
    pass

from domain.models.settings import ServiceSettings


class Config:
    """Base configuration. Values come from environment variables / src/.env."""
    DEBUG = False
    TESTING = False
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me-dev-secret-change-me")
    DEVICE_MASTER_KEY = os.getenv("DEVICE_MASTER_KEY", "dev-device-master-key")
    PAYMENT_WEBHOOK_SECRET = os.getenv("PAYMENT_WEBHOOK_SECRET", "dev-webhook-secret")
    # MySQL:  mysql+pymysql://user:password@127.0.0.1:3306/scentstation?charset=utf8mb4
    DATABASE_URI = os.getenv("DATABASE_URI", "mysql+pymysql://root:password@127.0.0.1:3306/scentstation?charset=utf8mb4")
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")
    # Development helpers (NEVER enable in production)
    MOCK_PAYMENT_ENABLED = os.getenv("MOCK_PAYMENT_ENABLED", "false").lower() == "true"
    SEED_SUPER_ADMIN_EMAIL = os.getenv("SEED_SUPER_ADMIN_EMAIL", "")
    SEED_SUPER_ADMIN_PASSWORD = os.getenv("SEED_SUPER_ADMIN_PASSWORD", "")

    HEARTBEAT_ONLINE_SECONDS = int(os.getenv("HEARTBEAT_ONLINE_SECONDS", "60"))
    HEARTBEAT_UNSTABLE_SECONDS = int(os.getenv("HEARTBEAT_UNSTABLE_SECONDS", "180"))
    ORDER_TTL_MINUTES = int(os.getenv("ORDER_TTL_MINUTES", "10"))
    COMMAND_TTL_SECONDS = int(os.getenv("COMMAND_TTL_SECONDS", "120"))
    TOKEN_TTL_MINUTES = int(os.getenv("TOKEN_TTL_MINUTES", "120"))
    STEP_UP_MINUTES = int(os.getenv("STEP_UP_MINUTES", "10"))

    @classmethod
    def service_settings(cls) -> ServiceSettings:
        return ServiceSettings(
            heartbeat_online_seconds=cls.HEARTBEAT_ONLINE_SECONDS,
            heartbeat_unstable_seconds=cls.HEARTBEAT_UNSTABLE_SECONDS,
            order_ttl_minutes=cls.ORDER_TTL_MINUTES, command_ttl_seconds=cls.COMMAND_TTL_SECONDS,
            token_ttl_minutes=cls.TOKEN_TTL_MINUTES, step_up_minutes=cls.STEP_UP_MINUTES)


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    DATABASE_URI = os.getenv("TEST_DATABASE_URI", "sqlite:///:memory:")
    MOCK_PAYMENT_ENABLED = True


class ProductionConfig(Config):
    DEBUG = False


class FactoryConfig:
    """Pick the configuration from FLASK_ENV (development | testing | production)."""

    @staticmethod
    def get_config(env: str = None):
        env = (env or os.getenv("FLASK_ENV", "development")).lower()
        return {"development": DevelopmentConfig, "testing": TestingConfig,
                "production": ProductionConfig}.get(env, DevelopmentConfig)
