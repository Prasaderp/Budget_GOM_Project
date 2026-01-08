import os
import glob
import logging
from sqlalchemy import text
from src.database import engine

logger = logging.getLogger(__name__)

MIGRATIONS_BASE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'migrations')
MIGRATION_ORDER = ['core', 'shared', 'schemes']

def ensure_migrations_table():
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id SERIAL PRIMARY KEY,
                version VARCHAR UNIQUE NOT NULL,
                executed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_schema_migrations_version ON schema_migrations(version)
        """))
        conn.execute(text("DELETE FROM schema_migrations WHERE executed_at IS NULL"))

def get_executed_migrations() -> set:
    ensure_migrations_table()
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version FROM schema_migrations"))
        return {row[0] for row in result}

def run_migration(version: str, sql_content: str):
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

def collect_migrations() -> list:
    """Collect all migrations in order: core -> shared -> schemes"""
    all_migrations = []
    
    for category in MIGRATION_ORDER:
        category_dir = os.path.join(MIGRATIONS_BASE, category)
        if not os.path.exists(category_dir):
            continue
        
        if category == 'schemes':
            for scheme_dir in sorted(glob.glob(os.path.join(category_dir, '*'))):
                if os.path.isdir(scheme_dir):
                    for sub_dir in sorted(glob.glob(os.path.join(scheme_dir, '*'))):
                        if os.path.isdir(sub_dir):
                            files = sorted(glob.glob(os.path.join(sub_dir, '*.sql')))
                            all_migrations.extend(files)
                    files = sorted(glob.glob(os.path.join(scheme_dir, '*.sql')))
                    all_migrations.extend(files)
        else:
            files = sorted(glob.glob(os.path.join(category_dir, '*.sql')))
            all_migrations.extend(files)
    
    return all_migrations

def run_migrations():
    if not os.path.exists(MIGRATIONS_BASE):
        logger.warning(f"Migrations directory not found: {MIGRATIONS_BASE}")
        return
    
    executed = get_executed_migrations()
    
    for migration_file in collect_migrations():
        rel_path = os.path.relpath(migration_file, MIGRATIONS_BASE)
        version = rel_path.replace(os.sep, '/')
        
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

