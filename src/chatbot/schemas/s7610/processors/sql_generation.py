from typing import Optional
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from ....llm import _init_llm
from ....core.schema_engine import schema_engine
from ....cache import TTLCache
from ..prompts.sql_prompt import SQL_PROMPT

_prompt_cache = TTLCache(maxsize=50, ttl=7200)

def _build_context_string(ctx) -> str:
    meta = ctx.metadata
    parts = []
    if meta.get('districts'):
        parts.append(f"Districts: {', '.join(meta['districts'])}")
    parts.append("Note: The 7610 scheme includes DCO Staff as a valid district entity.")
    parts.append("Konkan Division = all 7 regular districts combined (exclude DCO Staff for division aggregations)")
    parts.append("Mumbai Division = Mumbai City + Mumbai Suburban")
    return "\n".join(parts)

def _build_fiscal_columns_string(ctx) -> str:
    lines = []
    for key, cols in ctx.fiscal_column_map.items():
        lines.append(f"{key}: {', '.join(cols)}")
    return "\n".join(lines) if lines else "No fiscal columns detected"

def _build_examples(ctx) -> str:
    tn = ctx.table_names
    de = tn.get('district_expenditure', 'district_expenditure')
    default_fy = ctx.default_fiscal_year or '2025-26'
    
    return f"""Q: What is the expenditure for Mumbai City in 2023-24?
SQL: SELECT de."expenditure_2023_24", de."district", de."fiscal_year" FROM {de} de WHERE de."district" = 'Mumbai City' AND de."fiscal_year" = '{default_fy}' LIMIT {{top_k}};

Q: Show budget estimate for Palghar.
SQL: SELECT de."budget_estimate", de."district", de."fiscal_year" FROM {de} de WHERE de."district" = 'Palghar' AND de."fiscal_year" = '{default_fy}' LIMIT {{top_k}};

Q: What is the revised estimate for Thane?
SQL: SELECT de."revised_estimate", de."district", de."fiscal_year" FROM {de} de WHERE de."district" = 'Thane' AND de."fiscal_year" = '{default_fy}' LIMIT {{top_k}};

Q: What is the budget estimate for 2026-27 in Ratnagiri?
SQL: SELECT de."budget_estimate_2026_27", de."district", de."fiscal_year" FROM {de} de WHERE de."district" = 'Ratnagiri' AND de."fiscal_year" = '{default_fy}' LIMIT {{top_k}};

Q: Total expenditure in Konkan in 2022-23.
SQL: SELECT SUM(de."expenditure_2022_23") as total_expenditure, de."fiscal_year" FROM {de} de WHERE de."district" IN ('Mumbai City','Mumbai Suburban','Thane','Palghar','Raigad','Ratnagiri','Sindhudurg') AND de."fiscal_year" = '{default_fy}' GROUP BY de."fiscal_year";"""

def create_sql_chain(sub_scheme_code: Optional[str] = None):
    llm = _init_llm()
    ctx = schema_engine.build_context(sub_scheme_code)
    
    cache_key = f"prompt_s7610:{sub_scheme_code or 'default'}"
    cached = _prompt_cache.get(cache_key)
    
    if cached:
        sql_prompt, table_info = cached
    else:
        relevant_tables = schema_engine.detect_relevant_tables("", ctx)
        table_info = schema_engine.format_selective_table_info(ctx, relevant_tables)
        
        context_str = _build_context_string(ctx)
        fiscal_str = _build_fiscal_columns_string(ctx)
        examples_str = _build_examples(ctx)
        
        sql_prompt = SQL_PROMPT.partial(
            context=context_str,
            fiscal_columns=fiscal_str,
            examples=examples_str,
            default_fiscal_year=ctx.default_fiscal_year or '2025-26',
            available_fiscal_years=', '.join(ctx.available_fiscal_years) or 'unknown',
        )
        _prompt_cache.put(cache_key, (sql_prompt, table_info))
        
    chain = (
        {"input": RunnablePassthrough(), "top_k": RunnablePassthrough(), "table_info": RunnablePassthrough()}
        | sql_prompt
        | llm
        | StrOutputParser()
    )
    
    return chain, table_info
