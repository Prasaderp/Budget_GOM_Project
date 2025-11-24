import asyncio
import time
from .config import (
    connection_pool, executor, db_executor, dedup_lock, dedup_requests,
    MAX_WORKERS, MAX_CACHE_SIZE
)
from .database import init_connection_pool, schema_ttl_cache, get_db_connection, return_db_connection
from .cache import TTLCache
from .llm import _init_llm
from .processors import (
    preprocess_question, create_sql_chain, execute_query, generate_response
)
from .utils import validate_sql_query

query_ttl_cache = TTLCache(maxsize=500, ttl=600)

def get_request_id(query: str) -> str:
    import hashlib
    return hashlib.md5(query.encode()).hexdigest()

def initialize_chatbot():
    try:
        init_connection_pool()
        _init_llm()
        print("Chatbot initialization completed successfully")
    except Exception as e:
        print(f"Chatbot initialization failed: {e}")
        raise e

def cleanup_caches():
    try:
        query_ttl_cache.clear()
        schema_ttl_cache.clear()
        with dedup_lock:
            current_time = time.time()
            expired_keys = [k for k, f in dedup_requests.items() 
                          if current_time - getattr(f, '_created_time', current_time) > 300]
            for key in expired_keys:
                if key in dedup_requests:
                    del dedup_requests[key]
    except Exception as e:
        print(f"Cache cleanup error: {e}")

def chatbot(question: str, top_k: int = 10) -> str:
    start_time = time.time()
    request_id = get_request_id(f"{question}_{top_k}_{start_time}")
    
    print(f"\n--- Processing question {request_id[:8]} ---")
    print(f"Question: {question}")

    if not connection_pool:
        try:
            initialize_chatbot()
        except Exception as e:
            return f"System initialization failed: {str(e)}"

    original_question = question
    question = preprocess_question(question)
    if not question:
        return "Please provide a valid question."
    
    if question != original_question:
        print(f"Preprocessed from: '{original_question}' to: '{question}'")

    if any(division in question.lower() for division in ['konkan division', 'mumbai division', 'division']):
        top_k = max(100, top_k)
        print(f"Division query detected, using top_k={top_k}")

    try:
        print("Creating SQL generation chain...")
        sql_chain, table_info = create_sql_chain()

        print("Generating SQL query...")
        query_result = sql_chain.invoke({
            "input": question,
            "top_k": str(top_k),
            "table_info": table_info
        })

        generated_query = query_result.strip()
        print(f"Generated SQL: {generated_query}")

        if not generated_query or generated_query == "UNRELATED_QUERY_ATTEMPT":
            print(f"LLM indicated invalid/unrelated query: '{generated_query}'")
            return generate_response(question, generated_query or "Could not generate query.")

        is_valid, validation_message = validate_sql_query(generated_query)
        if not is_valid:
            print(f"SQL validation failed: {validation_message}")
            return generate_response(question, f"SQL_VALIDATION_ERROR: {validation_message}")

        print("Executing SQL query...")
        results = execute_query(generated_query, timeout=20)

        if isinstance(results, str) and results.startswith("DATABASE_ERROR"):
            print(f"Database error occurred: {results}")
            return generate_response(question, results)
        elif isinstance(results, str) and results.startswith("GENERAL_ERROR"):
            print(f"General error occurred: {results}")
            return generate_response(question, results)

        print("Generating final response...")
        response = generate_response(question, results)

        processing_time = time.time() - start_time
        print(f"--- Finished processing question {request_id[:8]} in {processing_time:.2f}s ---")
        return response

    except Exception as e:
        processing_time = time.time() - start_time
        print(f"Error during chatbot processing ({processing_time:.2f}s): {e}")
        return generate_response(question, f"GENERAL_ERROR: {str(e)}")
    finally:
        if time.time() % 100 < 1:
            cleanup_caches()

async def async_chatbot(question: str, top_k: int = 10) -> str:
    if not connection_pool:
        try:
            initialize_chatbot()
        except Exception as e:
            return f"System initialization failed: {str(e)}"
    
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, chatbot, question, top_k)

def shutdown_chatbot():
    try:
        if connection_pool:
            connection_pool.closeall()
        executor.shutdown(wait=True)
        db_executor.shutdown(wait=True)
        cleanup_caches()
        print("Chatbot shutdown completed")
    except Exception as e:
        print(f"Error during shutdown: {e}")

def get_system_stats():
    stats = {
        'connection_pool_status': 'initialized' if connection_pool else 'not_initialized',
        'executor_threads': len(executor._threads) if hasattr(executor, '_threads') else 0,
        'db_executor_threads': len(db_executor._threads) if hasattr(db_executor, '_threads') else 0,
        'schema_cache_size': len(schema_ttl_cache.cache),
        'query_cache_size': len(query_ttl_cache.cache),
        'pending_dedup_requests': len(dedup_requests),
        'circuit_breaker_state': getattr(connection_pool, '_circuit_breaker', {}).get('state', 'unknown'),
        'circuit_breaker_failures': getattr(connection_pool, '_circuit_breaker', {}).get('failures', 0)
    }
    return stats

if __name__ == "__main__":
    try:
        initialize_chatbot()
        print("Chatbot system ready for high-concurrency operations")
        print(f"Configuration: {MAX_WORKERS} workers, {MAX_CACHE_SIZE} cache size")
        print(f"System stats: {get_system_stats()}")
    except Exception as e:
        print(f"Failed to initialize chatbot: {e}")
        import sys
        sys.exit(1)
