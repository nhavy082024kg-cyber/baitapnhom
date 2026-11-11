from domain.models.irepositories import IUnitOfWork


class SqlAlchemyUnitOfWork(IUnitOfWork):
    """Wraps the request's scoped session: services call commit() once at the end of a use case."""

    def __init__(self, session):
        self.session = session

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()
