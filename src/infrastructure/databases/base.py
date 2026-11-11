from sqlalchemy.orm import declarative_base

# Every ORM model inherits Base; Base.metadata knows all tables (used by create_all and Alembic).
Base = declarative_base()
   