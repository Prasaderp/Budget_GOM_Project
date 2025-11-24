import os
from sqlalchemy import create_engine, event, pool
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool, QueuePool
from dotenv import load_dotenv
import logging

load_dotenv()

# NeonDB Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://neondb_owner:npg_G5JgHIM3YlCz@ep-holy-mode-a1lj6q7d-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require")

SQLALCHEMY_DATABASE_URL = DATABASE_URL

is_production = os.getenv("ENVIRONMENT", "development") == "production"

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
        "sslmode": "require",
        "connect_timeout": 10
    }
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

def init_db():
    from sqlalchemy import text
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE budget_post_details ADD COLUMN IF NOT EXISTS fiscal_year VARCHAR DEFAULT '2025-26'"))
        conn.execute(text("ALTER TABLE post_status ADD COLUMN IF NOT EXISTS fiscal_year VARCHAR DEFAULT '2025-26'"))
        conn.execute(text("ALTER TABLE post_expenses ADD COLUMN IF NOT EXISTS fiscal_year VARCHAR DEFAULT '2025-26'"))
        conn.execute(text("ALTER TABLE unit_expenditure ADD COLUMN IF NOT EXISTS fiscal_year VARCHAR DEFAULT '2025-26'"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_budget_fiscal_year ON budget_post_details(fiscal_year)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_budget_fiscal_district ON budget_post_details(fiscal_year, district)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_budget_full_lookup ON budget_post_details(fiscal_year, district, category, class_type, designation)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_post_status_fiscal_year ON post_status(fiscal_year)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_post_status_full_lookup ON post_status(fiscal_year, district, category, class_type, status)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_post_expenses_fiscal_year ON post_expenses(fiscal_year)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_post_expenses_full_lookup ON post_expenses(fiscal_year, district, category, class_type)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_unit_expenditure_fiscal_year ON unit_expenditure(fiscal_year)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_unit_expenditure_full_lookup ON unit_expenditure(fiscal_year, district, unit_account)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_messages_thread ON messages(thread_key)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_messages_from_to ON messages(from_username, to_username, created_at DESC)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_assistant_chats_user_created ON assistant_chats(username, created_at DESC)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_users_username_active ON users(username, is_active)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_admin_username ON admin_users(username)"))