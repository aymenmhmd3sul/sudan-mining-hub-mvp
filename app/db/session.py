from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings


DATABASE_URL = settings.DATABASE_URL

if not DATABASE_URL.startswith(
    ("postgresql://", "postgresql+psycopg2://")
):
    raise RuntimeError(
        "DATABASE_URL must point to PostgreSQL. "
        "SQLite is not allowed in the production MVP."
    )

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
