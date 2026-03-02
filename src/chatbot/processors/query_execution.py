import hashlib
import time
import psycopg2
from typing import Union, List, Tuple
from concurrent.futures import Future
from ..config import (
    MAX_QUERY_CACHE_SIZE, rate_limiter, dedup_lock, 
    dedup_requests, db_executor
)
from ..cache import TTLCache
from ..database import circuit_breaker, get_db_connection, return_db_connection

query_ttl_cache = TTLCache(maxsize=MAX_QUERY_CACHE_SIZE, ttl=120)

def get_request_id(query: str) -> str:
    return hashlib.md5(query.encode()).hexdigest()

@circuit_breaker
def execute_query(query: str, timeout: int = 15) -> Union[List[Tuple], str]:
    if not query or query.isspace():
        return "Could not generate query."

    if query.strip().upper() == "UNRELATED_QUERY_ATTEMPT":
        return "UNRELATED_QUERY_ATTEMPT"

    request_id = get_request_id(query)
    
    cached_result = query_ttl_cache.get(request_id)
    if cached_result is not None:
        return cached_result
    
    with dedup_lock:
        if request_id in dedup_requests:
            future = dedup_requests[request_id]
            try:
                result = future.result(timeout=timeout + 5)
                return result
            except Exception as e:
                print(f"Deduplication wait failed: {e}")
                pass
        
        future = Future()
        dedup_requests[request_id] = future

    def _execute():
        conn = None
        try:
            with rate_limiter:
                conn = get_db_connection(timeout=10)
                cursor = conn.cursor()
                cursor.execute(f"SET statement_timeout = '{timeout * 1000}'")
                print(f"Executing SQL: {query}")
                cursor.execute(query)

            if cursor.description:
                results = cursor.fetchall()
                print(f"Query returned {len(results)} rows.")

                if results:
                    column_names = [desc[0] for desc in cursor.description]
                    formatted_results = []
                    for row in results:
                        formatted_row = {}
                        for i, value in enumerate(row):
                            col_name = column_names[i]
                            if isinstance(value, (int, float)):
                                formatted_row[col_name] = f"{value:,}"
                            else:
                                formatted_row[col_name] = str(value)
                        formatted_results.append(formatted_row)
                    return formatted_results
                else:
                    return "NO_RECORDS_FOUND"
            else:
                result = f"Operation successful, {cursor.rowcount} rows affected."
                print(result)
                return result

        except psycopg2.Error as e:
            error_code = getattr(e, 'pgcode', 'UNKNOWN')
            error_message = getattr(e, 'pgerror', str(e))

            if error_code == '42P01':
                error_message = f"DATABASE_ERROR: Table does not exist. Please check the spelling and try again."
            elif error_code == '42703':
                error_message = f"DATABASE_ERROR: Column does not exist. Please check the column name and try again."
            elif error_code == '42601':
                error_message = f"DATABASE_ERROR: Invalid SQL syntax. Please rephrase your question."
            elif error_code == '23505':
                error_message = f"DATABASE_ERROR: Duplicate data constraint violation."
            else:
                error_message = f"DATABASE_ERROR: Code {error_code} - {error_message}"

            print(error_message)
            if conn:
                try:
                    conn.rollback()
                except Exception:
                    pass
            return error_message
        except Exception as e:
            error_message = f"GENERAL_ERROR: {str(e)}"
            print(error_message)
            if conn:
                try:
                    conn.rollback()
                except Exception:
                    pass
            return error_message
        finally:
            return_db_connection(conn)

    try:
        db_future = db_executor.submit(_execute)
        result = db_future.result(timeout=timeout)
        
        query_ttl_cache.put(request_id, result)
        
        with dedup_lock:
            if request_id in dedup_requests:
                if not future.done():
                    future.set_result(result)
                del dedup_requests[request_id]
        
        return result
    except Exception as e:
        print(f"Query execution timeout or error: {e}")
        error_result = f"GENERAL_ERROR: Query execution failed - {str(e)}"
        
        with dedup_lock:
            if request_id in dedup_requests:
                if not future.done():
                    future.set_result(error_result)
                del dedup_requests[request_id]
        
        return error_result
