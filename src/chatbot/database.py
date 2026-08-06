import time
import psycopg2
import psycopg2.extras
from psycopg2 import pool
from functools import wraps
from threading import Lock as _PoolLock
from typing import Dict, Any
from .config import (
    DB_NAME,
    DB_USER,
    DB_PASSWORD,
    DB_HOST,
    DB_PORT,
    DB_SSLMODE,
    CIRCUIT_BREAKER_THRESHOLD,
    CIRCUIT_BREAKER_TIMEOUT,
    connection_pool,
    db_circuit_breaker,
    circuit_breaker_lock,
)
from .cache import TTLCache

def circuit_breaker(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        with circuit_breaker_lock:
            if db_circuit_breaker['state'] == 'open':
                if time.time() - db_circuit_breaker['last_failure'] < CIRCUIT_BREAKER_TIMEOUT:
                    raise Exception("Circuit breaker is open - database unavailable")
                else:
                    db_circuit_breaker['state'] = 'half_open'
        
        try:
            result = func(*args, **kwargs)
            with circuit_breaker_lock:
                if db_circuit_breaker['state'] == 'half_open':
                    db_circuit_breaker['state'] = 'closed'
                    db_circuit_breaker['failures'] = 0
            return result
        except Exception as e:
            with circuit_breaker_lock:
                db_circuit_breaker['failures'] += 1
                db_circuit_breaker['last_failure'] = time.time()
                if db_circuit_breaker['failures'] >= CIRCUIT_BREAKER_THRESHOLD:
                    db_circuit_breaker['state'] = 'open'
            raise e
    return wrapper

_pool_init_lock = _PoolLock()

def init_connection_pool():
    global connection_pool
    with _pool_init_lock:
        if connection_pool is None:
            try:
                connection_pool = psycopg2.pool.ThreadedConnectionPool(
                    minconn=5,
                    maxconn=50,
                    dbname=DB_NAME,
                    user=DB_USER,
                    password=DB_PASSWORD,
                    host=DB_HOST,
                    port=DB_PORT,
                    connect_timeout=10,
                    application_name="gom_chatbot_pool",
                    sslmode=DB_SSLMODE,
                )
                print(f"Database connection pool initialized with 5-50 connections")
            except Exception as e:
                print(f"Failed to initialize connection pool: {e}")
                connection_pool = None

def get_db_connection(timeout=10):
    if connection_pool is None:
        init_connection_pool()
    if connection_pool is None:
        raise Exception("Database connection pool unavailable")
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            return connection_pool.getconn()
        except Exception as e:
            if "pool exhausted" in str(e).lower():
                time.sleep(0.1)
                continue
            raise e
    raise Exception("Database connection timeout - pool exhausted")

def return_db_connection(conn):
    if connection_pool and conn:
        try:
            connection_pool.putconn(conn)
        except Exception as e:
            print(f"Error returning connection to pool: {e}")

def is_pool_initialized():
    return connection_pool is not None

schema_ttl_cache = TTLCache(maxsize=10, ttl=900)

@circuit_breaker
def get_schema_info() -> Dict[str, Any]:
    cache_key = "schema_info"
    
    cached_result = schema_ttl_cache.get(cache_key)
    if cached_result is not None:
        return cached_result

    conn = None
    try:
        conn = get_db_connection(timeout=10)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cursor.execute("""
            SELECT table_name, table_type
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type IN ('BASE TABLE', 'VIEW')
            ORDER BY table_name
        """)
        tables = cursor.fetchall()

        schema_info = {}

        for table in tables:
            table_name = table['table_name']

            cursor.execute("""
                SELECT
                    column_name,
                    data_type,
                    is_nullable,
                    column_default,
                    character_maximum_length,
                    numeric_precision,
                    numeric_scale
                FROM information_schema.columns
                WHERE table_schema = 'public'
                AND table_name = %s
                ORDER BY ordinal_position
            """, (table_name,))

            columns = cursor.fetchall()

            cursor.execute("""
                SELECT column_name
                FROM information_schema.key_column_usage
                WHERE table_schema = 'public'
                AND table_name = %s
                AND constraint_name IN (
                    SELECT constraint_name
                    FROM information_schema.table_constraints
                    WHERE table_schema = 'public'
                    AND table_name = %s
                    AND constraint_type = 'PRIMARY KEY'
                )
            """, (table_name, table_name))

            primary_keys = [row['column_name'] for row in cursor.fetchall()]

            cursor.execute("""
                SELECT
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name
                FROM information_schema.key_column_usage kcu
                JOIN information_schema.constraint_column_usage ccu
                    ON kcu.constraint_name = ccu.constraint_name
                WHERE kcu.table_schema = 'public'
                AND kcu.table_name = %s
                AND kcu.constraint_name IN (
                    SELECT constraint_name
                    FROM information_schema.table_constraints
                    WHERE table_schema = 'public'
                    AND table_name = %s
                    AND constraint_type = 'FOREIGN KEY'
                )
            """, (table_name, table_name))

            foreign_keys = cursor.fetchall()

            cursor.execute("""
                SELECT
                    indexname,
                    indexdef
                FROM pg_indexes
                WHERE schemaname = 'public'
                AND tablename = %s
            """, (table_name,))

            indexes = cursor.fetchall()

            schema_info[table_name] = {
                'columns': columns,
                'primary_keys': primary_keys,
                'foreign_keys': foreign_keys,
                'indexes': indexes
            }

        cursor.close()
        
        schema_ttl_cache.put(cache_key, schema_info)
        return schema_info

    except Exception as e:
        print(f"Error getting schema information: {e}")
        raise e
    finally:
        return_db_connection(conn)

