import re
from typing import Tuple
from .schema_engine import SchemaContext


def validate_sql(query: str, ctx: SchemaContext) -> Tuple[bool, str]:
    if not query or query.isspace():
        return False, "Empty query"

    stripped = query.strip()
    if stripped.upper() == "UNRELATED_QUERY_ATTEMPT":
        return True, "Unrelated"

    if ";" in stripped[:-1]:
        return False, "Multiple statements not allowed"

    upper = stripped.upper()
    if not upper.startswith('SELECT'):
        return False, "Only SELECT allowed"

    dangerous = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'CREATE', 'ALTER',
                  'TRUNCATE', 'GRANT', 'REVOKE', 'EXEC', 'EXECUTE']
    for kw in dangerous:
        if kw in upper and not upper.startswith('SELECT'):
            return False, f"Dangerous operation: {kw}"

    suspicious = ['--', '/*', '*/', 'UNION SELECT', 'UNION ALL SELECT',
                  'INFORMATION_SCHEMA', 'PG_SLEEP', 'WAITFOR', 'INTO']
    for p in suspicious:
        if p in upper:
            return False, f"Suspicious pattern: {p}"

    if 'FROM' not in upper:
        return False, "Missing FROM clause"

    if stripped.count("'") % 2 != 0:
        return False, "Unmatched quotes"

    limit_m = re.search(r'\bLIMIT\s+(\d+)', upper)
    if limit_m:
        if int(limit_m.group(1)) > 1000:
            return False, "LIMIT too large"

    has_agg = any(a in upper for a in ['SUM(', 'COUNT(', 'AVG(', 'MIN(', 'MAX('])
    if has_agg and 'GROUP BY' not in upper:
        return False, "Aggregation without GROUP BY"

    lower = stripped.lower()
    for table_name in ctx.all_columns:
        if table_name.lower() in lower:
            break
    else:
        known = list(ctx.table_names.values())
        if not any(t.lower() in lower for t in known):
            return False, "Query references unknown tables"

    return True, "Valid"


def validate_columns_exist(query: str, ctx: SchemaContext) -> Tuple[bool, str]:
    col_pattern = re.compile(r'"([a-z_][a-z0-9_]*)"', re.I)
    found_cols = col_pattern.findall(query)

    all_known_cols = set()
    for cols in ctx.all_columns.values():
        all_known_cols.update(c.lower() for c in cols)

    table_alias_cols = {'district', 'category', 'class_type', 'designation',
                        'status', 'unit_account', 'fiscal_year', 'id',
                        'scheme_code', 'sub_scheme_code'}
    all_known_cols.update(table_alias_cols)

    for col in found_cols:
        if col.lower() not in all_known_cols:
            return False, f"Column '{col}' does not exist in schema"

    return True, "Columns valid"
