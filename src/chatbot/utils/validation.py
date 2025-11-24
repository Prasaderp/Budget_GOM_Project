from typing import Tuple

def validate_sql_query(query: str) -> Tuple[bool, str]:
    if not query:
        return False, "Empty query"

    query_upper = query.upper().strip()
    query_lower = query.lower().strip()

    dangerous_keywords = [
        'DROP', 'DELETE', 'UPDATE', 'INSERT', 'CREATE', 'ALTER',
        'TRUNCATE', 'GRANT', 'REVOKE', 'EXEC', 'EXECUTE'
    ]

    for keyword in dangerous_keywords:
        if keyword in query_upper and not query_upper.startswith('SELECT'):
            return False, f"Query contains potentially dangerous operation: {keyword}"

    if not query_upper.startswith('SELECT'):
        return False, "Only SELECT queries are allowed"

    suspicious_patterns = [
        '--', '/*', '*/', 'UNION SELECT', 'UNION ALL SELECT',
        'INFORMATION_SCHEMA', 'PG_SLEEP', 'WAITFOR', 'INTO'
    ]

    for pattern in suspicious_patterns:
        if pattern in query_upper:
            return False, f"Suspicious pattern detected: {pattern}"

    if 'SELECT' in query_upper:
        if 'FROM' not in query_upper:
            return False, "Query must contain FROM clause"

        single_quotes = query.count("'")
        if single_quotes % 2 != 0:
            return False, "Unmatched single quotes in query"

    # Enhanced logical validation
    # Check for proper aggregation with GROUP BY
    if any(agg in query_upper for agg in ['SUM(', 'COUNT(', 'AVG(', 'MIN(', 'MAX(']):
        if 'GROUP BY' not in query_upper:
            return False, "Aggregation functions require GROUP BY clause"
    
    # Check for table aliases in joins
    if 'JOIN' in query_upper and 'ON' in query_upper:
        # Look for potential column ambiguity
        if '"district"' in query_lower and query_lower.count('"district"') > 1:
            if not any(alias in query_lower for alias in ['bpd.', 'ps.', 'pe.', 'ue.']):
                return False, "Multi-table queries require table aliases to avoid column ambiguity"
    
    # Check for proper post counting
    if 'sanctioned_posts' in query_lower:
        if not ('sanctioned_posts_2024_25' in query_lower and 'sanctioned_posts_2025_26' in query_lower):
            return False, "Post counting should include both 2024-25 and 2025-26 years"
    
    # Check for proper LIMIT in division queries
    if any(div in query_lower for div in ['konkan division', 'mumbai division']):
        if 'LIMIT 10' in query_upper:
            return False, "Division queries should use higher LIMIT (50+) to show all districts"

    return True, "Query validated"
