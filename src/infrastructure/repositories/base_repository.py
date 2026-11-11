from dataclasses import fields
from typing import List, Optional

from sqlalchemy.exc import IntegrityError


class SqlRepository:
    """
    Generic helpers shared by all repositories.
      * ORM row  <->  domain dataclass (fields with the same name)
      * repositories only flush(); the use case commits through the UnitOfWork
    Subclasses set `model` (ORM class) and `entity` (domain dataclass).
    """
    model = None
    entity = None

    def __init__(self, session):
        self.session = session

    # -- mapping ------------------------------------------------------------------
    def _to_entity(self, row):
        if row is None:
            return None
        return self.entity(**{f.name: getattr(row, f.name) for f in fields(self.entity)})

    def _to_entities(self, rows) -> List:
        return [self._to_entity(r) for r in rows]

    # -- write --------------------------------------------------------------------
    def _add(self, entity):
        # None values are skipped so column defaults (created_at, status...) still apply
        data = {f.name: getattr(entity, f.name) for f in fields(entity) if getattr(entity, f.name) is not None}
        row = self.model(**data)
        self.session.add(row)
        self.session.flush()
        return self._to_entity(row)

    def _save(self, entity):
        row = self.session.query(self.model).filter_by(id=entity.id).one()
        for f in fields(entity):
            if f.name not in ("id", "created_at"):
                setattr(row, f.name, getattr(entity, f.name))
        self.session.flush()
        return self._to_entity(row)

    def _add_if_new(self, entity) -> bool:
        """INSERT inside a SAVEPOINT: a UNIQUE violation (duplicate event) rolls back only this insert."""
        data = {f.name: getattr(entity, f.name) for f in fields(entity) if getattr(entity, f.name) is not None}
        try:
            with self.session.begin_nested():
                self.session.add(self.model(**data))
                self.session.flush()
        except IntegrityError:
            return False
        return True

    # -- read ---------------------------------------------------------------------
    def _first(self, **filters):
        return self._to_entity(self.session.query(self.model).filter_by(**filters).first())

    def _all(self, **filters) -> List:
        return self._to_entities(self.session.query(self.model).filter_by(**filters).order_by(self.model.id).all())
