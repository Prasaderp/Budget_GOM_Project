import asyncio
import time
from typing import Optional
from .config import connection_pool, executor, db_executor, dedup_lock, dedup_requests, MAX_WORKERS, MAX_CACHE_SIZE
from .database import init_connection_pool, schema_ttl_cache, get_db_connection, return_db_connection
from .cache import TTLCache
from .llm import _init_llm
from .processors.query_execution import execute_query
from .schemas.registry import chatbot_schema_registry
from .security import get_policy_for_subscheme
from .core.schema_engine import schema_engine
from .core.query_classifier import query_classifier, fast_path_engine, semantic_cache
from .core.sql_validator import validate_sql, validate_columns_exist
from src.utils_scheme import FOUR_TABLE_PARENT_SCHEMES

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
        semantic_cache.clear()
        with dedup_lock:
            current_time = time.time()
            expired = [k for k, f in dedup_requests.items()
                       if current_time - getattr(f, '_created_time', current_time) > 300]
            for key in expired:
                dedup_requests.pop(key, None)
    except Exception as e:
        print(f"Cache cleanup error: {e}")


def chatbot(
    question: str,
    top_k: int = 10,
    sub_scheme_code: Optional[str] = None,
    user_context: Optional[dict] = None,
) -> str:
    start_time = time.time()
    request_id = get_request_id(f"{question}_{top_k}_{start_time}")

    print(f"\n--- Processing {request_id[:8]} ---")
    print(f"Q: {question}")
    if sub_scheme_code:
        print(f"Scheme: {sub_scheme_code}")

    if not connection_pool:
        try:
            initialize_chatbot()
        except Exception as e:
            return f"System initialization failed: {str(e)}"

    policy = get_policy_for_subscheme(sub_scheme_code)

    original_question = question
    allowed, secured_question = policy.enforce_question(original_question, user_context)
    if not allowed:
        processors = chatbot_schema_registry.get_processors(sub_scheme_code)
        if processors:
            _, _, generate_response = processors
            return generate_response(original_question, f"SECURITY_POLICY: {secured_question}")
        return f"SECURITY_POLICY: {secured_question}"

    question = secured_question

    processors = chatbot_schema_registry.get_processors(sub_scheme_code)
    if not processors:
        return f"Error: Could not load processors for scheme {sub_scheme_code}"

    preprocess_question, create_sql_chain, generate_response = processors
    question = preprocess_question(question)
    if not question:
        return "Please provide a valid question."

    if question != original_question:
        print(f"Preprocessed: '{question}'")

    cached = semantic_cache.get(question, sub_scheme_code or '')
    if cached:
        print(f"Semantic cache hit ({time.time() - start_time:.2f}s)")
        return cached

    scheme_code = chatbot_schema_registry.get_scheme_code(sub_scheme_code)

    try:
        ctx = schema_engine.build_context(sub_scheme_code)
    except Exception as e:
        print(f"Schema context error: {e}")
        ctx = None

    if ctx:
        qtype, match_data = query_classifier.classify(question, ctx)
        if qtype != 'llm' and match_data:
            print(f"Fast path: {qtype}")
            fast_sql = fast_path_engine.generate_sql(qtype, match_data, question, ctx, top_k)
            if fast_sql:
                valid, msg = validate_sql(fast_sql, ctx)
                if valid:
                    results = execute_query(fast_sql, timeout=15)
                    response = generate_response(question, results)
                    semantic_cache.put(question, sub_scheme_code or '', response)
                    print(f"Fast path done ({time.time() - start_time:.2f}s)")
                    return response
                else:
                    print(f"Fast path validation failed: {msg}, falling back to LLM")

    if scheme_code in FOUR_TABLE_PARENT_SCHEMES and any(
        d in question.lower() for d in ['konkan division', 'mumbai division', 'division']
    ):
        top_k = max(100, top_k)

    try:
        print("LLM SQL generation...")
        sql_chain, table_info = create_sql_chain(sub_scheme_code)

        if ctx:
            relevant_tables = schema_engine.detect_relevant_tables(question, ctx)
            table_info = schema_engine.format_selective_table_info(ctx, relevant_tables)
            print(f"Selective tables: {relevant_tables}")

        max_retries = 2
        generated_query = None

        for attempt in range(max_retries + 1):
            query_result = sql_chain.invoke({
                "input": question if attempt == 0 else f"{question}\n\nPREVIOUS ERROR: {error_msg}. Fix the SQL.",
                "top_k": str(top_k),
                "table_info": table_info
            })

            generated_query = query_result.strip()
            print(f"SQL (attempt {attempt + 1}): {generated_query}")

            if not generated_query or generated_query == "UNRELATED_QUERY_ATTEMPT":
                return generate_response(question, generated_query or "Could not generate query.")

            if ctx:
                valid, error_msg = validate_sql(generated_query, ctx)
                if not valid:
                    print(f"Validation failed: {error_msg}")
                    if attempt < max_retries:
                        continue
                    return generate_response(question, f"SQL_VALIDATION_ERROR: {error_msg}")

                col_valid, col_msg = validate_columns_exist(generated_query, ctx)
                if not col_valid:
                    print(f"Column check failed: {col_msg}")
                    if attempt < max_retries:
                        error_msg = col_msg
                        continue
                    return generate_response(question, f"SQL_VALIDATION_ERROR: {col_msg}")
            break

        allowed_sql, secured_sql = policy.enforce_sql(generated_query, user_context)
        if not allowed_sql:
            return generate_response(question, f"SECURITY_POLICY: {secured_sql}")

        generated_query = secured_sql

        print("Executing SQL...")
        results = execute_query(generated_query, timeout=20)

        if isinstance(results, str) and (results.startswith("DATABASE_ERROR") or results.startswith("GENERAL_ERROR")):
            print(f"DB error: {results}")
            return generate_response(question, results)

        response = generate_response(question, results)
        semantic_cache.put(question, sub_scheme_code or '', response)

        print(f"Done ({time.time() - start_time:.2f}s)")
        return response

    except Exception as e:
        print(f"Error ({time.time() - start_time:.2f}s): {e}")
        return generate_response(question, f"GENERAL_ERROR: {str(e)}")
    finally:
        if time.time() % 100 < 1:
            cleanup_caches()


async def async_chatbot(
    question: str,
    top_k: int = 10,
    sub_scheme_code: Optional[str] = None,
    user_context: Optional[dict] = None,
) -> str:
    if not connection_pool:
        try:
            initialize_chatbot()
        except Exception as e:
            return f"System initialization failed: {str(e)}"

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        executor, chatbot, question, top_k, sub_scheme_code, user_context,
    )


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
    return {
        'connection_pool_status': 'initialized' if connection_pool else 'not_initialized',
        'executor_threads': len(executor._threads) if hasattr(executor, '_threads') else 0,
        'db_executor_threads': len(db_executor._threads) if hasattr(db_executor, '_threads') else 0,
        'schema_cache_size': len(schema_ttl_cache.cache),
        'query_cache_size': len(query_ttl_cache.cache),
        'semantic_cache_entries': len(semantic_cache._cache.cache),
        'pending_dedup_requests': len(dedup_requests),
    }
