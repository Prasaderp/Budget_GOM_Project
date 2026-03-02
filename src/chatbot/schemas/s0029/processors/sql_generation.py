from typing import Optional
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from ....llm import _init_llm
from ....core.schema_engine import schema_engine
from ....cache import TTLCache
from ..prompts.sql_prompt import SQL_PROMPT
from src.schemes.s0029.subs.s0029.config import get_all_table_sections

_prompt_cache = TTLCache(maxsize=50, ttl=900)

def _build_context_string(ctx) -> str:
    meta = ctx.metadata
    parts = []
    
    # Override districts to show only 6 districts for 0029
    districts = ['Mumbai City', 'Mumbai Suburban', 'Thane', 'Raigad', 'Ratnagiri', 'Sindhudurg']
    parts.append(f"Districts: {', '.join(districts)} (NOTE: Palghar and DCO Staff are NOT valid districts for 0029)")
    
    parts.append("\nRevenue Section Codes (table_section_code):")
    sections = get_all_table_sections()
    for s in sections:
        parts.append(f" - {s['code']}: {s['text_en']}")
        
    return "\n".join(parts)

def _build_fiscal_columns_string(ctx) -> str:
    lines = []
    for key, cols in ctx.fiscal_column_map.items():
        lines.append(f"{key}: {', '.join(cols)}")
    return "\n".join(lines) if lines else "No fiscal columns detected"

def _build_examples(ctx) -> str:
    tn = ctx.table_names
    dr = tn.get('district_revenue', 'district_revenue_0029')
    default_fy = ctx.default_fiscal_year
    
    return f"""Q: What is the actual receipt for Mumbai City in 2017-18?
SQL: SELECT dr."actual_2017_18", dr."district", dr."table_section_code", dr."fiscal_year" FROM {dr} dr WHERE dr."district" = 'Mumbai City' AND dr."fiscal_year" = '{default_fy}' LIMIT {{top_k}};

Q: Show budget estimate for land revenue (00290258) in Thane for 2020-21.
SQL: SELECT dr."budget_estimate_2020_21", dr."district", dr."fiscal_year" FROM {dr} dr WHERE dr."district" = 'Thane' AND dr."table_section_code" = '00290258' AND dr."fiscal_year" = '{default_fy}' LIMIT {{top_k}};

Q: Total actual receipts in Konkan for 2018-19.
SQL: SELECT SUM(dr."actual_2018_19") as total_actual, dr."table_section_code", dr."fiscal_year" FROM {dr} dr WHERE dr."district" IN ('Mumbai City','Mumbai Suburban','Thane','Raigad','Ratnagiri','Sindhudurg') AND dr."fiscal_year" = '{default_fy}' GROUP BY dr."table_section_code", dr."fiscal_year";"""

def create_sql_chain(sub_scheme_code: Optional[str] = None):
    llm = _init_llm()
    ctx = schema_engine.build_context(sub_scheme_code)
    
    cache_key = f"prompt_s0029:{sub_scheme_code or 'default'}:{ctx.default_fiscal_year}"
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
            default_fiscal_year=ctx.default_fiscal_year,
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
