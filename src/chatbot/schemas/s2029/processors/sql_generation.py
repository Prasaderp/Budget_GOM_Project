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
    if meta.get('categories'):
        parts.append(f"Categories: {', '.join(repr(c) for c in meta['categories'])} (case-sensitive)")
    if meta.get('classes'):
        parts.append(f"Classes: {', '.join(repr(c) for c in meta['classes'])} (exact format)")
    if meta.get('designations'):
        desigs = meta['designations'][:15]
        parts.append(f"Designations: {', '.join(repr(d) for d in desigs)}"
                     + (f" ... ({len(meta['designations'])} total)" if len(meta['designations']) > 15 else ""))
    if meta.get('primary_units'):
        units = meta['primary_units'][:10]
        parts.append(f"Unit Accounts: {', '.join(repr(u) for u in units)}"
                     + (f" ... ({len(meta['primary_units'])} total)" if len(meta['primary_units']) > 10 else ""))
    if meta.get('designations_mr'):
        mr_samples = list(meta['designations_mr'].items())[:8]
        parts.append("Marathi→English: " + ", ".join(f"'{m}'→'{e}'" for m, e in mr_samples))
    return "\n".join(parts)


def _build_fiscal_columns_string(ctx) -> str:
    lines = []
    for key, cols in ctx.fiscal_column_map.items():
        lines.append(f"{key}: {', '.join(cols)}")
    return "\n".join(lines) if lines else "No fiscal columns detected"


def _build_examples(ctx) -> str:
    tn = ctx.table_names
    bpd = tn.get('budget_post_details', 'budget_post_details')
    ue = tn.get('unit_expenditure', 'unit_expenditure')
    pe = tn.get('post_expenses', 'post_expenses')

    desigs = ctx.metadata.get('designations', ['Deputy Collector/Expert Officer'])
    desig = desigs[0] if desigs else 'Deputy Collector/Expert Officer'
    units = ctx.metadata.get('primary_units', ['01- Salary'])
    unit = units[0] if units else '01- Salary'

    fy_cols = ctx.fiscal_column_map
    exp_col = 'expenditure_2022_23'
    for cols in fy_cols.values():
        for c in cols:
            if 'expenditure' in c and '2022' in c:
                exp_col = c
                break

    sanc_cols = [c for cols in fy_cols.values() for c in cols if 'sanctioned_posts' in c]
    sanc_sum = ' + '.join(f'bpd."{c}"' for c in sanc_cols) if sanc_cols else 'bpd."sanctioned_posts_2024_25" + bpd."sanctioned_posts_2025_26"'

    default_fy = ctx.default_fiscal_year or '2025-26'

    return f"""Q: What is the basic pay for {desig} in Mumbai City?
SQL: SELECT bpd."basic_pay", bpd."designation", bpd."district", bpd."category", bpd."fiscal_year" FROM {bpd} bpd WHERE bpd."district" = 'Mumbai City' AND bpd."designation" = '{desig}' AND bpd."fiscal_year" = '{default_fy}' AND bpd."basic_pay" > 0 ORDER BY bpd."basic_pay" DESC LIMIT {{top_k}};

Q: Show expenditure for Palghar in 2022-23
SQL: SELECT ue."district", ue."unit_account", ue."{exp_col}", ue."fiscal_year" FROM {ue} ue WHERE ue."district" = 'Palghar' AND ue."fiscal_year" = '{default_fy}' LIMIT {{top_k}};

Q: How many vacant posts in Mumbai Suburban?
SQL: SELECT SUM(pe."vacant_posts") as total_vacant, pe."district", pe."fiscal_year" FROM {pe} pe WHERE pe."district" = 'Mumbai Suburban' AND pe."fiscal_year" = '{default_fy}' GROUP BY pe."district", pe."fiscal_year";

Q: Total posts of {desig} in Thane
SQL: SELECT SUM({sanc_sum}) as total_posts, bpd."district", bpd."designation", bpd."fiscal_year" FROM {bpd} bpd WHERE bpd."district" = 'Thane' AND bpd."designation" = '{desig}' AND bpd."fiscal_year" = '{default_fy}' GROUP BY bpd."district", bpd."designation", bpd."fiscal_year" LIMIT {{top_k}};

Q: What is the grade pay of Deputy Collector/Expert Officer in Mumbai City of Permanent position in 2032-33
SQL: SELECT bpd."grade_pay", bpd."designation", bpd."district", bpd."category", bpd."fiscal_year" FROM {bpd} bpd WHERE bpd."district" = 'Mumbai City' AND bpd."designation" = 'Deputy Collector/Expert Officer' AND bpd."category" = 'Permanent' AND bpd."fiscal_year" = '2032-33' AND bpd."grade_pay" > 0 ORDER BY bpd."grade_pay" DESC LIMIT {{top_k}};

Q: Medical expenses for Mumbai City
SQL: SELECT "district", MAX("medical_expenses") as medical_expenses, "fiscal_year" FROM {pe} WHERE "district" = 'Mumbai City' AND "fiscal_year" = '{default_fy}' GROUP BY "district", "fiscal_year" LIMIT {{top_k}};

Q: Districtwise Class-3 data of Konkan Division
SQL: SELECT bpd."district", bpd."designation", bpd."category", bpd."sanctioned_posts_2024_25", bpd."basic_pay", bpd."fiscal_year" FROM {bpd} bpd WHERE bpd."class_type" = 'Class-3' AND bpd."district" IN ('Mumbai City','Mumbai Suburban','Thane','Palghar','Raigad','Ratnagiri','Sindhudurg') AND bpd."fiscal_year" = '{default_fy}' ORDER BY bpd."district", bpd."designation" LIMIT 100;"""


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
