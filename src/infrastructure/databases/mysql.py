from infrastructure.databases.abstract_database import AbstractDatabase
from infrastructure.databases.base import Base
from infrastructure.databases.seed import seed_defaults


class DatabaseMySQL(AbstractDatabase):
    """MySQL 8 through PyMySQL:  mysql+pymysql://user:password@host:3306/scentstation"""

    def __init__(self, database_uri: str = None):
        super().__init__(database_uri)

    def engine_options(self) -> dict:
        return {"pool_pre_ping": True, "pool_recycle": 3600}

    def init_database(self, app) -> None:
        import infrastructure.models  # noqa: F401  (register every model in Base.metadata BEFORE create_all)
        Base.metadata.create_all(bind=self.engine)
        seed_defaults(self.session, app.config)
        self.session.remove()
