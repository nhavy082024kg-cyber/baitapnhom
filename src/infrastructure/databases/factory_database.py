from infrastructure.databases.abstract_database import AbstractDatabase
from infrastructure.databases.mysql import DatabaseMySQL
from infrastructure.databases.sqlite import DatabaseSQLite


class FactoryDatabase:
    """Chooses the database adapter from the URI scheme. Add DatabasePostgres here to support another DB."""

    @staticmethod
    def get_database(database_uri: str = None) -> AbstractDatabase:
        from config import FactoryConfig
        uri = database_uri or FactoryConfig.get_config().DATABASE_URI
        if uri.startswith("sqlite"):
            return DatabaseSQLite(uri)
        if uri.startswith("mysql"):
            return DatabaseMySQL(uri)
        raise ValueError(f"Unsupported DATABASE_URI scheme: {uri.split(':')[0]}")
