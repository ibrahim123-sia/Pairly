from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from config import get_config

config = get_config()



def normalize_db_url(url):
    """Pin the PostgreSQL driver to psycopg2 (the one in requirements.txt).

    Hosts hand out postgres:// or postgresql:// URLs. SQLAlchemy 2.1 maps a
    bare postgresql:// to psycopg (v3) instead of psycopg2, so the driver is
    always named explicitly.
    """
    for prefix in ("postgres://", "postgresql://"):
        if url and url.startswith(prefix):
            return "postgresql+psycopg2://" + url[len(prefix):]
    return url


db_url = normalize_db_url(config.SQLALCHEMY_DATABASE_URI)

# Enable connection pooling and pre-ping for PostgreSQL robustness
connect_args = {}
if db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine_kwargs = {"pool_pre_ping": True, "connect_args": connect_args}
if not db_url.startswith("sqlite"):
    # Connection pooling tuning only applies to server databases (e.g. PostgreSQL).
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20

engine = create_engine(db_url, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
