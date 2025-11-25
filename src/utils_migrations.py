import os
import glob
import logging
from sqlalchemy import text
from sqlalchemy.orm import Session
from src.database import engine
from src import models

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'migrations')

def ensure_migrations_table():
    """Create schema_migrations table if it doesn't exist"""
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id SERIAL PRIMARY KEY,
                version VARCHAR UNIQUE NOT NULL,
                executed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_schema_migrations_version 
            ON schema_migrations(version)
        """))
        conn.execute(text("DELETE FROM schema_migrations WHERE executed_at IS NULL"))

def get_executed_migrations() -> set:
    """Get set of executed migration versions"""
    ensure_migrations_table()
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version FROM schema_migrations"))
        return {row[0] for row in result}

def run_migration(version: str, sql_content: str):
    """Execute a single migration with increased timeout"""
    with engine.begin() as conn:
        try:
            conn.execute(text("SET statement_timeout = '300000'"))
            conn.execute(text(sql_content))
            conn.execute(text(
                "INSERT INTO schema_migrations (version, executed_at) VALUES (:version, CURRENT_TIMESTAMP)"
            ), {"version": version})
            logger.info(f"Migration {version} executed successfully")
        except Exception as e:
            logger.error(f"Migration {version} failed: {e}", exc_info=True)
            raise

def run_migrations():
    """Run all pending migrations"""
    if not os.path.exists(MIGRATIONS_DIR):
        logger.warning(f"Migrations directory not found: {MIGRATIONS_DIR}")
        return
    
    executed = get_executed_migrations()
    migration_files = sorted(glob.glob(os.path.join(MIGRATIONS_DIR, '*.sql')))
    
    for migration_file in migration_files:
        version = os.path.basename(migration_file)
        if version in executed:
            logger.debug(f"Migration {version} already executed, skipping")
            continue
        
        logger.info(f"Running migration: {version}")
        try:
            with open(migration_file, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            run_migration(version, sql_content)
        except Exception as e:
            logger.error(f"Failed to run migration {version}: {e}", exc_info=True)
            raise

