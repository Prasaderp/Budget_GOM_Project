from typing import Optional
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from ....llm import _init_llm
from ....core.schema_engine import schema_engine
from ....cache import TTLCache
from ..prompts.sql_prompt import SQL_PROMPT

_prompt_cache = TTLCache(maxsize=50, ttl=900)

def _build_context_string(ctx) -> str:
    meta = ctx.metadata
    parts = []
    parts.append("Scheme 2075: Miscellaneous General Services - Pension Expenditure")
    parts.append("Two tables are used:")
    parts.append("1. Sub-head expenditure (sub_scheme_code='20750249', DCO only, single row)")
    parts.append("2. District-wise expenditure (sub_scheme_code='20750294', 4 regular districts)")
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
    she = tn.get('sub_head_expenditure', 'sub_head_expenditure_2075')
    de = tn.get('district_expenditure', 'district_expenditure_2075')

    default_fy = ctx.default_fiscal_year
    exp_cols = [c for cols in ctx.fiscal_column_map.values() for c in cols if 'expenditure' in c]
    exp_1 = exp_cols[0] if exp_cols else 'expenditure'
    exp_list = ', '.join(f'"{c}"' for c in exp_cols[:3]) if exp_cols else '"expenditure"'

    return f"""Q: What is the sub-head expenditure?
SQL: SELECT "sub_head", "{exp_1}" FROM {she} WHERE "fiscal_year" = '{default_fy}' AND "sub_scheme_code" = '20750249';

Q: Total budget estimate across all districts
SQL: SELECT SUM("budget_estimate") as total FROM {de} WHERE "fiscal_year" = '{default_fy}' AND "sub_scheme_code" = '20750294';

Q: Show Thane district expenditure trends
SQL: SELECT "district", {exp_list} FROM {de} WHERE "fiscal_year" = '{default_fy}' AND "sub_scheme_code" = '20750294' AND "district" = 'Thane';"""

def create_sql_chain(sub_scheme_code: Optional[str] = None):
    llm = _init_llm()
    ctx = schema_engine.build_context(sub_scheme_code)

    cache_key = f"prompt_v3:{sub_scheme_code or 'default'}:{ctx.default_fiscal_year}"
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
