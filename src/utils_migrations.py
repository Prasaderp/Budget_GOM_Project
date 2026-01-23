"""
Migration Runner with Precise Error Detection and Line-by-Line Execution.

Features:
- Runs each SQL statement one-by-one within a single transaction
- Pinpoints exact file, line number, and statement on error
- Detailed logging with timestamps and execution duration
- No data skipping - fails fast with complete error context
- Tracks original line numbers from source files
- Handles PostgreSQL dollar-quoted strings (DO $$ ... $$;)
- Handles UTF-8 BOM in SQL files
"""

import os
import glob
import logging
import re
import time
from dataclasses import dataclass
from typing import Optional
from sqlalchemy import text
from src.database import engine

logger = logging.getLogger(__name__)

MIGRATIONS_BASE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'migrations')
MIGRATION_ORDER = ['core', 'shared', 'schemes']


@dataclass
class StatementInfo:
    """Holds metadata for a single SQL statement."""
    content: str
    start_line: int
    end_line: int
    statement_index: int


@dataclass
class MigrationError:
    """Detailed error context for migration failures."""
    file_path: str
    file_name: str
    statement_index: int
    start_line: int
    end_line: int
    statement_preview: str
    error_message: str
    error_type: str

    def format_error(self) -> str:
        """Format error for logging with full context."""
        separator = "=" * 80
        return f"""
{separator}
MIGRATION FAILURE DETECTED
{separator}

FILE:       {self.file_path}
STATEMENT:  #{self.statement_index + 1}
LINE RANGE: {self.start_line} - {self.end_line}
ERROR TYPE: {self.error_type}

ERROR MESSAGE:
{self.error_message}

FAILING STATEMENT (first 500 chars):
{self.statement_preview[:500]}{'...' if len(self.statement_preview) > 500 else ''}

{separator}
"""


def parse_sql_statements(sql_content: str) -> list[StatementInfo]:
    """
    Parse SQL content into individual statements with line tracking.
    
    Handles:
    - Multi-line statements
    - Comments (-- and /* */)
    - Strings with embedded semicolons
    - PostgreSQL dollar-quoted strings (DO $$ ... $$;)
    - Empty statements
    - Transaction control statements (BEGIN/COMMIT) at file level only
    
    Returns list of StatementInfo with original line numbers preserved.
    """
    statements: list[StatementInfo] = []
    lines = sql_content.split('\n')
    
    current_statement_lines: list[str] = []
    current_start_line: int = 1
    in_block_comment = False
    in_string = False
    string_char = ''
    paren_depth = 0
    in_dollar_quote = False
    dollar_quote_tag = ''
    
    for line_num, line in enumerate(lines, start=1):
        stripped = line.strip()
        
        # Check if we're NOT inside any quoted/comment context
        if not in_dollar_quote and not in_string and not in_block_comment:
            # Skip empty lines and single-line comments when not accumulating
            if not stripped or stripped.startswith('--'):
                if not current_statement_lines:
                    current_start_line = line_num + 1
                continue
            
            # Skip transaction control ONLY when NOT accumulating a statement
            # This prevents skipping PL/pgSQL BEGIN inside DO blocks
            upper_stripped = stripped.upper()
            if upper_stripped in ('BEGIN;', 'BEGIN', 'COMMIT;', 'COMMIT'):
                if not current_statement_lines:
                    current_start_line = line_num + 1
                    continue
        
        if not current_statement_lines:
            current_start_line = line_num
        
        current_statement_lines.append(line)
        
        # Character-by-character parsing for proper delimiter detection
        i = 0
        line_len = len(stripped)
        while i < line_len:
            char = stripped[i]
            
            # Inside dollar-quoted block - only look for closing tag
            if in_dollar_quote:
                if char == '$':
                    end_pos = stripped.find('$', i + 1)
                    if end_pos != -1:
                        potential_tag = stripped[i:end_pos + 1]
                        if potential_tag == dollar_quote_tag:
                            in_dollar_quote = False
                            dollar_quote_tag = ''
                            i = end_pos + 1
                            continue
                i += 1
                continue
            
            # Inside block comment - only look for closing */
            if in_block_comment:
                if char == '*' and i + 1 < line_len and stripped[i + 1] == '/':
                    in_block_comment = False
                    i += 1
                i += 1
                continue
            
            # Start of block comment
            if char == '/' and i + 1 < line_len and stripped[i + 1] == '*':
                in_block_comment = True
                i += 2
                continue
            
            # Start of line comment - skip rest of line
            if char == '-' and i + 1 < line_len and stripped[i + 1] == '-':
                break
            
            # Inside regular string - only look for closing quote
            if in_string:
                if char == string_char:
                    if i + 1 < line_len and stripped[i + 1] == string_char:
                        i += 2
                        continue
                    in_string = False
                i += 1
                continue
            
            # Start of dollar-quoted string ($$, $tag$, etc.)
            if char == '$':
                end_pos = stripped.find('$', i + 1)
                if end_pos != -1:
                    dollar_quote_tag = stripped[i:end_pos + 1]
                    in_dollar_quote = True
                    i = end_pos + 1
                    continue
                i += 1
                continue
            
            # Start of regular string
            if char in ("'", '"'):
                in_string = True
                string_char = char
                i += 1
                continue
            
            # Track parentheses depth
            if char == '(':
                paren_depth += 1
            elif char == ')':
                paren_depth -= 1
            elif char == ';' and paren_depth == 0:
                # End of statement
                full_statement = '\n'.join(current_statement_lines).strip()
                if full_statement and not full_statement.endswith(';'):
                    full_statement += ';'
                
                if full_statement and full_statement != ';':
                    statements.append(StatementInfo(
                        content=full_statement,
                        start_line=current_start_line,
                        end_line=line_num,
                        statement_index=len(statements)
                    ))
                
                current_statement_lines = []
                remaining = stripped[i + 1:].strip()
                if remaining and remaining != ';':
                    current_statement_lines = [remaining]
                    current_start_line = line_num
                else:
                    current_start_line = line_num + 1
                paren_depth = 0
                break
            
            i += 1
    
    # Handle any remaining content
    if current_statement_lines:
        final_stmt = '\n'.join(current_statement_lines).strip()
        if final_stmt:
            statements.append(StatementInfo(
                content=final_stmt,
                start_line=current_start_line,
                end_line=len(lines),
                statement_index=len(statements)
            ))
    
    return statements


def ensure_migrations_table():
    """Create migrations tracking table if not exists."""
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
    """Get set of already executed migration versions."""
    ensure_migrations_table()
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version FROM schema_migrations"))
        return {row[0] for row in result}


def run_migration(version: str, sql_content: str, file_path: str) -> Optional[MigrationError]:
    """
    Execute a migration file statement-by-statement with precise error tracking.
    
    Args:
        version: Migration version identifier
        sql_content: Raw SQL file content
        file_path: Absolute path to migration file (for error reporting)
    
    Returns:
        None on success, MigrationError on failure
    
    Notes:
        - All statements execute within a single transaction
        - On any error, entire migration is rolled back
        - No data is skipped - fails on first error
    """
    file_name = os.path.basename(file_path)
    statements = parse_sql_statements(sql_content)
    total_statements = len(statements)
    
    if total_statements == 0:
        logger.warning(f"[{version}] No executable statements found - skipping")
        return None
    
    logger.info(f"[{version}] Starting migration: {total_statements} statements to execute")
    start_time = time.time()
    
    with engine.begin() as conn:
        try:
            conn.execute(text("SET statement_timeout = '300000'"))
            
            for stmt_info in statements:
                stmt_num = stmt_info.statement_index + 1
                
                if stmt_num % 50 == 0 or stmt_num == total_statements:
                    logger.debug(f"[{version}] Progress: {stmt_num}/{total_statements} statements")
                
                try:
                    conn.execute(text(stmt_info.content))
                except Exception as stmt_error:
                    error = MigrationError(
                        file_path=file_path,
                        file_name=file_name,
                        statement_index=stmt_info.statement_index,
                        start_line=stmt_info.start_line,
                        end_line=stmt_info.end_line,
                        statement_preview=stmt_info.content,
                        error_message=str(stmt_error),
                        error_type=type(stmt_error).__name__
                    )
                    logger.error(error.format_error())
                    raise
            
            conn.execute(text(
                "INSERT INTO schema_migrations (version, executed_at) "
                "VALUES (:version, CURRENT_TIMESTAMP)"
            ), {"version": version})
            
            elapsed = time.time() - start_time
            logger.info(
                f"[{version}] Migration completed successfully: "
                f"{total_statements} statements in {elapsed:.2f}s"
            )
            return None
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(
                f"[{version}] Migration FAILED after {elapsed:.2f}s - "
                f"transaction rolled back, no data committed"
            )
            raise


def collect_migrations() -> list[tuple[str, str]]:
    """
    Collect all migration files in execution order.
    
    Order: core -> shared -> schemes (sorted alphabetically within each)
    
    Returns:
        List of tuples: (version_string, absolute_file_path)
    """
    all_migrations: list[tuple[str, str]] = []
    
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
                            for f in files:
                                rel = os.path.relpath(f, MIGRATIONS_BASE).replace(os.sep, '/')
                                all_migrations.append((rel, f))
                    files = sorted(glob.glob(os.path.join(scheme_dir, '*.sql')))
                    for f in files:
                        rel = os.path.relpath(f, MIGRATIONS_BASE).replace(os.sep, '/')
                        all_migrations.append((rel, f))
        else:
            files = sorted(glob.glob(os.path.join(category_dir, '*.sql')))
            for f in files:
                rel = os.path.relpath(f, MIGRATIONS_BASE).replace(os.sep, '/')
                all_migrations.append((rel, f))
    
    return all_migrations


def run_migrations():
    """
    Execute all pending migrations in order.
    
    Behavior:
        - Runs migrations sequentially (core -> shared -> schemes)
        - Stops immediately on first failure
        - Each migration is atomic (all-or-nothing)
        - Already executed migrations are skipped
        - Provides detailed error context on failure
    """
    if not os.path.exists(MIGRATIONS_BASE):
        logger.warning(f"Migrations directory not found: {MIGRATIONS_BASE}")
        return
    
    executed = get_executed_migrations()
    migrations = collect_migrations()
    pending = [(v, p) for v, p in migrations if v not in executed]
    
    if not pending:
        logger.info("All migrations already executed - nothing to do")
        return
    
    logger.info(f"Found {len(pending)} pending migration(s) to execute")
    
    total_start = time.time()
    
    for version, file_path in pending:
        logger.info(f"{'=' * 60}")
        logger.info(f"Executing: {version}")
        
        try:
            # Use utf-8-sig to automatically strip BOM if present
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                sql_content = f.read()
            
            run_migration(version, sql_content, file_path)
            
        except Exception as e:
            total_elapsed = time.time() - total_start
            logger.error(f"Migration run aborted after {total_elapsed:.2f}s")
            logger.error(f"Failed migration: {version}")
            logger.error(f"Review the error above for exact file, line, and statement details")
            raise
    
    total_elapsed = time.time() - total_start
    logger.info(f"{'=' * 60}")
    logger.info(f"All {len(pending)} migration(s) completed successfully in {total_elapsed:.2f}s")