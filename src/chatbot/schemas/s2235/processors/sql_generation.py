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
    districts = meta.get('districts') or []
    if districts:
        parts.append(f"Districts: {', '.join(districts)}")
    non_regular = {'DCO Staff', 'Divisional Commissioner'}
    regular = [d for d in districts if d not in non_regular]
    excluded = [d for d in districts if d in non_regular]
    if regular and excluded:
        parts.append(f"Regular Districts (exclude {', '.join(excluded)} for aggregations): "
                     f"{', '.join(regular)}")
        parts.append(f"Konkan Division = all {len(regular)} regular districts combined")
    elif regular:
        parts.append(f"Konkan Division = all {len(regular)} districts combined")
    return "\n".join(parts)


def _build_fiscal_columns_string(ctx) -> str:
    lines = []
    for key, cols in ctx.fiscal_column_map.items():
        lines.append(f"{key}: {', '.join(cols)}")
    return "\n".join(lines) if lines else "No fiscal columns detected"


def _build_examples(ctx) -> str:
    tn = ctx.table_names.get('district_expenditure', 'district_expenditure_table')
    default_fy = ctx.default_fiscal_year or '2025-26'

    # Discover expenditure column from fiscal map
    exp_col = 'expenditure_2022_23'
    for cols in ctx.fiscal_column_map.values():
        for c in cols:
            if 'expenditure' in c and '2022' in c:
                exp_col = c
                break

    # Discover revised column from live schema
    revised_col = 'revised_grant_2025_26'
    for c in ctx.all_columns.get(tn, []):
        if 'revised_grant' in c:
            revised_col = c
            break
        elif 'revised_estimate' in c:
            revised_col = c
            break

    # Build district lists dynamically from actual config
    districts = ctx.metadata.get('districts') or []
    non_regular = {'DCO Staff', 'Divisional Commissioner'}
    regular = [d for d in districts if d not in non_regular]
    sample_district = 'Thane' if 'Thane' in districts else (districts[0] if districts else 'Thane')
    # Second sample: pick a different district for variety
    sample_district2 = next((d for d in regular if d != sample_district), sample_district)
    regular_in_clause = ', '.join(f"'{d}'" for d in regular)
    excluded = [d for d in districts if d in non_regular]
    exclude_clause = ' AND '.join(f"de.\"district\" != '{d}'" for d in excluded)

    examples = f"""Q: What is the expenditure of {sample_district} in 2022-23?
SQL: SELECT de."district", de."{exp_col}", de."fiscal_year" FROM {tn} de WHERE de."district" = '{sample_district}' AND de."fiscal_year" = '{default_fy}' LIMIT {{top_k}};

Q: Show revised grant for {sample_district2}
SQL: SELECT de."district", de."{revised_col}", de."fiscal_year" FROM {tn} de WHERE de."district" = '{sample_district2}' AND de."fiscal_year" = '{default_fy}' LIMIT {{top_k}};

Q: Total expenditure for Konkan division in 2022-23
SQL: SELECT SUM(de."{exp_col}") as total, de."fiscal_year" FROM {tn} de WHERE de."district" IN ({regular_in_clause})"""

    if exclude_clause:
        examples += f" AND {exclude_clause}"
    examples += f" AND de.\"fiscal_year\" = '{default_fy}' GROUP BY de.\"fiscal_year\";"

    return examples


def create_sql_chain(sub_scheme_code: Optional[str] = None):
    llm = _init_llm()
    ctx = schema_engine.build_context(sub_scheme_code)

    cache_key = f"prompt_v3_s2235:{sub_scheme_code or 'default'}"
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
