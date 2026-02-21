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
    parts.append("Scheme 2215: Water Scarcity Expenditure")
    parts.append("Single table: district_expenditure_2215")
    parts.append("Key identifiers: 'account_head_code' (e.g. 2215A195, 2215A201) and 'district' (ILIKE match for offices)")
    if meta.get('districts'):
        parts.append(f"Districts: {', '.join(meta['districts'])}")
    return "\n".join(parts)

def _build_fiscal_columns_string(ctx) -> str:
    lines = []
    for key, cols in ctx.fiscal_column_map.items():
        lines.append(f"{key}: {', '.join(cols)}")
    return "\n".join(lines) if lines else "No fiscal columns detected"

def _build_examples(ctx) -> str:
    tn = ctx.table_names
    de = tn.get('district_expenditure', 'district_expenditure_2215')

    default_fy = ctx.default_fiscal_year or '2025-26'

    return f"""Q: What is the expenditure for Thane in 2022-23 for account head 2215A195?
SQL: SELECT district, expenditure_2022_23 FROM {de} WHERE fiscal_year = '{default_fy}' AND account_head_code = '2215A195' AND district ILIKE '%Thane%';

Q: Total budget estimate across all districts for 2215A201
SQL: SELECT SUM(budget_estimate) as total FROM {de} WHERE fiscal_year = '{default_fy}' AND account_head_code = '2215A201';

Q: Show Palghar district expenditure trends
SQL: SELECT district, expenditure_2022_23, expenditure_2023_24, expenditure_2024_25 FROM {de} WHERE fiscal_year = '{default_fy}' AND district ILIKE '%Palghar%';"""

def create_sql_chain(sub_scheme_code: Optional[str] = None):
    llm = _init_llm()
    ctx = schema_engine.build_context(sub_scheme_code)

    cache_key = f"prompt_v3:{sub_scheme_code or 'default'}"
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
