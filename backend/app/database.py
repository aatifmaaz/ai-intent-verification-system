from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker
from .config import settings

engine = create_engine(
    settings.database_url, connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
)

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if settings.database_url.startswith("sqlite"):
        try:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
        except Exception:
            pass

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def init_db(engine_to_use=None):
    import app.models  # Ensure all models are registered
    target_engine = engine_to_use or engine
    Base.metadata.create_all(bind=target_engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

