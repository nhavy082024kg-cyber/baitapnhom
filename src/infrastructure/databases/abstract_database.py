from abc import ABC, abstractmethod

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from config import FactoryConfig


class AbstractDatabase(ABC):
    """
    One engine + one scoped_session (one session per request/thread, shared by every repository,
    so a whole use case runs in ONE transaction).
    """

    def __init__(self, database_uri: str = None):
        self.database_uri = database_uri or FactoryConfig.get_config().DATABASE_URI
        self.engine = create_engine(self.database_uri, **self.engine_options())
        self.session = scoped_session(sessionmaker(autoflush=False, bind=self.engine))

    def engine_options(self) -> dict:
        return {"pool_pre_ping": True}

    @abstractmethod
    def init_database(self, app) -> None:
        """Create tables / seed reference data."""

    def remove_session(self) -> None:
        self.session.remove()
