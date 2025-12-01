import os
from sqlalchemy import create_engine, event, pool
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool, QueuePool
from dotenv import load_dotenv
import logging

load_dotenv()

# NeonDB Configuration
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set. Please configure it in your .env file.")

SQLALCHEMY_DATABASE_URL = DATABASE_URL

is_production = os.getenv("ENVIRONMENT", "development") == "production"

_DB_SSLMODE = os.getenv(
    "DB_SSLMODE",
    "require" if not any(h in (DATABASE_URL or "") for h in ("localhost", "127.0.0.1")) else "disable",
)

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20 if is_production else 10,
    max_overflow=30 if is_production else 15,
    pool_pre_ping=True,
    pool_recycle=600,
    pool_timeout=30,
    echo=False,
    pool_reset_on_return='rollback',
    connect_args={
        "sslmode": _DB_SSLMODE,
        "connect_timeout": 10,
    },
)

@event.listens_for(engine, "connect")
def set_postgresql_params(dbapi_conn, connection_record):
    """Set PostgreSQL session parameters after connection"""
    try:
        with dbapi_conn.cursor() as cursor:
            cursor.execute("SET statement_timeout = '20000'")
            cursor.execute("SET jit = 'off'")
            cursor.execute("SET random_page_cost = 1.1")
            cursor.execute("SET effective_cache_size = '4GB'")
            cursor.execute("SET work_mem = '16MB'")
    except Exception as e:
        logging.warning(f"Could not set PostgreSQL parameters: {e}")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def run_database_migrations():
    """Run database migrations on startup"""
    from src.utils_migrations import run_migrations
    try:
        run_migrations()
    except Exception as e:
        logging.error(f"Migration failed: {e}", exc_info=True)
        raise