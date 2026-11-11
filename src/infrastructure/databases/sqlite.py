from sqlalchemy.pool import StaticPool

from infrastructure.databases.abstract_database import AbstractDatabase
from infrastructure.databases.base import Base
from infrastructure.databases.seed import seed_defaults


class DatabaseSQLite(AbstractDatabase):
    """Only for quick local experiments / automated tests (DATABASE_URI=sqlite:///:memory:)."""

    def engine_options(self) -> dict:
        options = {"connect_args": {"check_same_thread": False}}
        if ":memory:" in self.database_uri:
            options["poolclass"] = StaticPool      # keep ONE connection, otherwise the memory DB disappears
        return options

    def init_database(self, app) -> None:
        import infrastructure.models  # noqa: F401
        Base.metadata.create_all(bind=self.engine)
        seed_defaults(self.session, app.config)
        self.session.remove()
