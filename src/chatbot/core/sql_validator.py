import re
from typing import Tuple
from .schema_engine import SchemaContext

_DANGEROUS_KW_PATTERN = re.compile(
    r'\b(DROP|DELETE|UPDATE|INSERT|CREATE|ALTER|TRUNCATE|GRANT|REVOKE|EXECUTE|COPY)\b'
)

_DANGEROUS_FUNC_PATTERN = re.compile(
    r'\b(pg_read_file|pg_ls_dir|pg_stat_file|lo_import|lo_export'
    r'|pg_sleep|dblink|dblink_exec)\s*\(', re.I
)


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

    # Word-boundary check for DML/DDL keywords even inside SELECT queries
    # (defense-in-depth against subquery injection)
    dml_match = _DANGEROUS_KW_PATTERN.search(upper)
    if dml_match:
        return False, f"Dangerous operation: {dml_match.group(1)}"

    func_match = _DANGEROUS_FUNC_PATTERN.search(stripped)
    if func_match:
        return False, f"Dangerous function: {func_match.group(1)}"

    suspicious = ['--', '/*', '*/',
                  'INFORMATION_SCHEMA', 'PG_SLEEP', 'WAITFOR']
    for p in suspicious:
        if p in upper:
            return False, f"Suspicious pattern: {p}"

    # Block SELECT ... INTO (write operation), but not "INTO" inside string literals
    if re.search(r'\bINTO\b', upper):
        # Only block if INTO appears outside single-quoted strings
        outside_strings = re.sub(r"'[^']*'", '', upper)
        if re.search(r'\bINTO\b', outside_strings):
            return False, "SELECT INTO not allowed"

    if 'FROM' not in upper:
        return False, "Missing FROM clause"

    if stripped.count("'") % 2 != 0:
        return False, "Unmatched quotes"

    limit_m = re.search(r'\bLIMIT\s+(\d+)', upper)
    if limit_m:
        if int(limit_m.group(1)) > 1000:
            return False, "LIMIT too large"

    # Only reject aggregations without GROUP BY when non-aggregate columns
    # are also selected (standalone SUM/COUNT/etc. are valid without GROUP BY)
    has_agg = any(a in upper for a in ['SUM(', 'COUNT(', 'AVG(', 'MIN(', 'MAX('])
    if has_agg and 'GROUP BY' not in upper:
        # Extract the SELECT clause (before FROM)
        select_clause = upper.split('FROM')[0] if 'FROM' in upper else upper
        # Remove aggregate expressions to see if bare columns remain
        bare = re.sub(r'(SUM|COUNT|AVG|MIN|MAX)\s*\([^)]*\)', '', select_clause)
        bare = re.sub(r'\bAS\s+\w+', '', bare)  # remove aliases
        bare = re.sub(r'SELECT|DISTINCT|,|\s+', ' ', bare).strip()
        # If non-whitespace remains after removing aggregates/aliases/keywords,
        # there are bare columns → GROUP BY is required
        remaining = [t for t in bare.split() if t and t != '*']
        if remaining:
            # Check if remaining tokens are string literals (e.g. 'Sub-head')
            non_literal = [t for t in remaining if not t.startswith("'")]
            if non_literal:
                return False, "Aggregation with non-aggregate columns requires GROUP BY"

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
    found_identifiers = col_pattern.findall(query)

    # Extract aliases defined via AS (table and column aliases) so we skip them
    alias_pattern = re.compile(r'\bAS\s+"?([a-z_]\w*)"?', re.I)
    query_aliases = {m.lower() for m in alias_pattern.findall(query)}

    # Build set of known table names so we can skip them
    known_tables = set()
    for tname in ctx.all_columns:
        known_tables.add(tname.lower())
    for tname in ctx.table_names.values():
        if tname:
            known_tables.add(tname.lower())

    # Build set of known column names from live schema discovery
    all_known_cols = set()
    for cols in ctx.all_columns.values():
        all_known_cols.update(c.lower() for c in cols)

    # Common columns that appear across schemes but may not surface in
    # per-table discovery (e.g. used only in WHERE or aliased queries)
    common_cols = {'district', 'category', 'class_type', 'designation',
                   'status', 'unit_account', 'fiscal_year', 'id',
                   'scheme_code', 'sub_scheme_code', 'account_head_code',
                   'sub_head', 'remarks', 'table_section_code'}
    all_known_cols.update(common_cols)

    for ident in found_identifiers:
        ident_lower = ident.lower()
        # Skip table names and AS aliases — both are double-quoted in PostgreSQL
        if ident_lower in known_tables or ident_lower in query_aliases:
            continue
        if ident_lower not in all_known_cols:
            return False, f"Column '{ident}' does not exist in schema"

    return True, "Columns valid"
