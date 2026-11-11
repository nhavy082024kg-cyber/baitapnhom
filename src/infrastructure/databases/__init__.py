from functools import lru_cache

from infrastructure.databases.abstract_database import AbstractDatabase


@lru_cache(maxsize=1)
def get_database() -> AbstractDatabase:
    """Single shared database object (engine + scoped session) for the whole process."""
    from infrastructure.databases.factory_database import FactoryDatabase
    return FactoryDatabase.get_database()


def init_db(app) -> None:
    """Called by create_app(): create tables, seed roles/permissions, release the session after each request."""
    database = get_database()
    database.init_database(app)

    @app.teardown_appcontext
    def _remove_session(exception=None):
        database.remove_session()           # un-committed work is rolled back automatically
