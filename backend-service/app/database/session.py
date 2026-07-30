from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from pgvector.psycopg import register_vector

from app.core.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
)

@event.listens_for(engine, "connect")
def register_pgvector_connection(dbapi_connection, connection_record):
    register_vector(dbapi_connection)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()