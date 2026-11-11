from sqlalchemy import BigInteger, Column, DateTime, Enum, ForeignKey, Integer
from sqlalchemy.dialects import mysql

from domain.clock import utcnow


def id_type():
    """BIGINT UNSIGNED on MySQL (as in ERD.md), plain INTEGER on SQLite so autoincrement works there."""
    return BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql").with_variant(Integer(), "sqlite")


def fk(target: str, nullable: bool = True, **kwargs) -> Column:
    """Foreign-key column (indexed). Example: tenant_id = fk('tenants.id', nullable=False)"""
    return Column(id_type(), ForeignKey(target), nullable=nullable, index=True, **kwargs)


def enum_col(enum_cls, nullable: bool = False, default=None, **kwargs) -> Column:
    """ENUM column built from a domain enum, so DB values and domain/constants.py can never drift apart."""
    return Column(Enum(*[e.value for e in enum_cls], name=enum_cls.__name__.lower()), nullable=nullable,
                  default=default.value if default is not None else None, **kwargs)


class IdMixin:
    id = Column(id_type(), primary_key=True, autoincrement=True)


class TimestampMixin:
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)
