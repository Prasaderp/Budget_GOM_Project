from typing import Optional
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from ....llm import _init_llm
from ....core.schema_engine import schema_engine
from ....cache import TTLCache
from ..prompts.sql_prompt import SQL_PROMPT

_prompt_cache = TTLCache(maxsize=50, ttl=900)

def _build_context_string(ctx) -> str:
    parts = [
        "Scheme 6245: Other Loans for Natural Calamities",
        "Single table: district_expenditure_62450017",
        "Key identifier: 'district' (exact string match for 5 Konkan districts)"
    ]
    if districts := ctx.metadata.get('districts'):
        parts.append(f"Districts: {', '.join(districts)}")
    return "\n".join(parts)

def _build_fiscal_columns_string(ctx) -> str:
    return "\n".join(f"{k}: {', '.join(v)}" for k, v in ctx.fiscal_column_map.items()) or "No fiscal columns detected"

def _build_examples(ctx) -> str:
    tn = ctx.table_names.get('district_expenditure', 'district_expenditure_62450017')
    fy = ctx.default_fiscal_year
    exp_cols = [c for cols in ctx.fiscal_column_map.values() for c in cols if 'expenditure' in c]
    exp_1 = exp_cols[0] if exp_cols else 'expenditure'
    exp_list = ', '.join(f'"{c}"' for c in exp_cols[:3]) if exp_cols else '"expenditure"'
    return f"""Q: What is the expenditure for Thane?
SQL: SELECT "district", "{exp_1}" FROM {tn} WHERE "fiscal_year" = '{fy}' AND "district" = 'Thane';

Q: Show Palghar district expenditure trends
SQL: SELECT "district", {exp_list} FROM {tn} WHERE "fiscal_year" = '{fy}' AND "district" = 'Palghar';"""

def create_sql_chain(sub_scheme_code: Optional[str] = None):
    ctx = schema_engine.build_context(sub_scheme_code)
    cache_key = f"prompt_s6245:{sub_scheme_code or 'default'}:{ctx.default_fiscal_year}"
    
    if not (cached := _prompt_cache.get(cache_key)):
        relevant_tables = schema_engine.detect_relevant_tables("", ctx)
        table_info = schema_engine.format_selective_table_info(ctx, relevant_tables)
        sql_prompt = SQL_PROMPT.partial(
            context=_build_context_string(ctx),
            fiscal_columns=_build_fiscal_columns_string(ctx),
            examples=_build_examples(ctx),
            default_fiscal_year=ctx.default_fiscal_year,
            available_fiscal_years=', '.join(ctx.available_fiscal_years) or 'unknown',
        )
        _prompt_cache.put(cache_key, (sql_prompt, table_info))
    else:
        sql_prompt, table_info = cached

    chain = (
        {"input": RunnablePassthrough(), "top_k": RunnablePassthrough(), "table_info": RunnablePassthrough()}
        | sql_prompt | _init_llm() | StrOutputParser()
    )
    return chain, table_info
