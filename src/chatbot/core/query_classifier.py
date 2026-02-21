import re
import hashlib
from typing import Optional, Tuple, List, Dict
from .schema_engine import SchemaContext


def _extract_fiscal_year_from_question(question: str) -> str:
    """Extract fiscal year from question text. Returns '' if none found."""
    m = re.search(r'(\d{4})[-/](\d{2,4})', question)
    if not m:
        return ""
    y1, y2 = m.group(1), m.group(2)
    if len(y2) == 4:
        y2 = y2[2:]
    return f"{y1}-{y2}"


def _resolve_fiscal_year(question: str, ctx: SchemaContext) -> str:
    """Resolve the fiscal year to use for a query.
    
    1. If user specified a fiscal year in the question, use it (after validation).
    2. Otherwise, use the default fiscal year from the schema context.
    """
    user_fy = _extract_fiscal_year_from_question(question)
    if user_fy:
        # Validate against available fiscal years
        if user_fy in ctx.available_fiscal_years:
            return user_fy
        # Try whitespace-trimmed match
        for fy in ctx.available_fiscal_years:
            if fy.strip() == user_fy.strip():
                return fy
        # User asked for a FY that doesn't exist — still return it so the query yields
        # an empty result (which is correct behavior) rather than returning all FYs
        return user_fy
    return ctx.default_fiscal_year


class QueryClassifier:
    FAST_PATTERNS = [
        (re.compile(r'(?:total|how many|count)\s+(?:filled|vacant)\s+posts?\s+(?:in|for)\s+(.+)', re.I),
         'post_count'),
        (re.compile(r'(?:total|sum|what is)\s+(?:budget|expenditure)\s+(?:for|in|of)\s+(.+)', re.I),
         'expenditure_sum'),
        (re.compile(r'(basic|grade|special)\s+pay(?:\s+(?:of|for|across|in))?\s+(.*)', re.I),
         'pay_lookup'),
    ]

    def classify(self, question: str, ctx: SchemaContext) -> Tuple[str, Optional[Dict]]:
        q = question.strip()
        for pattern, qtype in self.FAST_PATTERNS:
            m = pattern.search(q)
            if m:
                return qtype, {'groups': m.groups()}
        return 'llm', None


class FastPathEngine:
    def generate_sql(self, qtype: str, match_data: Dict,
                     question: str, ctx: SchemaContext, top_k: int = 10) -> Optional[str]:
        groups = match_data.get('groups', ())
        fiscal_year = _resolve_fiscal_year(question, ctx)

        if qtype == 'post_count':
            return self._post_count_sql(groups, question, ctx, top_k, fiscal_year)
        if qtype == 'expenditure_sum':
            return self._expenditure_sum_sql(groups, question, ctx, top_k, fiscal_year)
        if qtype == 'pay_lookup':
            return self._pay_lookup_sql(groups, question, ctx, top_k, fiscal_year)
        return None

    def _build_fy_condition(self, alias: str, fiscal_year: str, ctx: SchemaContext) -> str:
        """Build a fiscal_year WHERE clause fragment if the table has a fiscal_year column."""
        if not fiscal_year or not ctx.has_fiscal_year_column():
            return ''
        return f'{alias}."fiscal_year" = \'{fiscal_year}\''

    def _post_count_sql(self, groups: tuple, question: str, ctx: SchemaContext,
                        top_k: int, fiscal_year: str) -> Optional[str]:
        pe_table = ctx.table_names.get('post_expenses')
        if not pe_table:
            return None
        district = self._extract_district(groups[0], ctx) if groups[0] else None
        q_lower = question.lower()
        col = 'filled_posts' if 'filled' in q_lower else 'vacant_posts'
        conditions = []
        if district:
            conditions.append(f'pe."district" = \'{district}\'')
        fy_cond = self._build_fy_condition('pe', fiscal_year, ctx)
        if fy_cond:
            conditions.append(fy_cond)
        where = (' WHERE ' + ' AND '.join(conditions)) if conditions else ''
        return (f'SELECT pe."district", pe."fiscal_year", SUM(pe."{col}") as total_{col} '
                f'FROM {pe_table} pe{where} '
                f'GROUP BY pe."district", pe."fiscal_year" ORDER BY total_{col} DESC LIMIT {top_k};')

    def _expenditure_sum_sql(self, groups: tuple, question: str, ctx: SchemaContext,
                             top_k: int, fiscal_year: str) -> Optional[str]:
        ue_table = ctx.table_names.get('unit_expenditure')
        if not ue_table:
            return None
        fy_cols = []
        for key, cols in ctx.fiscal_column_map.items():
            if key.startswith('expenditure') or key.startswith('budget'):
                fy_cols.extend(cols)
        q_lower = question.lower()
        year_match = re.search(r'(\d{4})[-_](\d{2,4})', q_lower)
        target_col = None
        if year_match:
            y1, y2 = year_match.group(1), year_match.group(2)
            if len(y2) == 2:
                target_pattern = f'{y1}_{y2}'
            else:
                target_pattern = f'{y1}_{y2[2:]}'
            for c in fy_cols:
                if target_pattern in c:
                    target_col = c
                    break
        if not target_col and fy_cols:
            target_col = fy_cols[-1]
        if not target_col:
            return None
        district = self._extract_district(groups[0] if groups else '', ctx)
        conditions = []
        if district:
            conditions.append(f'ue."district" = \'{district}\'')
        fy_cond = self._build_fy_condition('ue', fiscal_year, ctx)
        if fy_cond:
            conditions.append(fy_cond)
        where = (' WHERE ' + ' AND '.join(conditions)) if conditions else ''
        return (f'SELECT ue."district", ue."unit_account", ue."fiscal_year", SUM(ue."{target_col}") as total '
                f'FROM {ue_table} ue{where} '
                f'GROUP BY ue."district", ue."unit_account", ue."fiscal_year" ORDER BY total DESC LIMIT {top_k};')

    def _pay_lookup_sql(self, groups: tuple, question: str, ctx: SchemaContext,
                       top_k: int, fiscal_year: str) -> Optional[str]:
        bpd_table = ctx.table_names.get('budget_post_details')
        if not bpd_table:
            return None
        
        pay_type = groups[0].lower().strip() if len(groups) > 0 else 'basic'
        pay_col = f'{pay_type}_pay'
        
        rest_of_text = groups[1].strip() if len(groups) > 1 and groups[1] else ''
        
        designation = self._extract_designation(rest_of_text, ctx)
        district = self._extract_district(rest_of_text, ctx)
        
        conditions = []
        if designation:
            conditions.append(f'bpd."designation" = \'{designation}\'')
        if district:
            conditions.append(f'bpd."district" = \'{district}\'')
        
        fy_cond = self._build_fy_condition('bpd', fiscal_year, ctx)
        if fy_cond:
            conditions.append(fy_cond)
            
        conditions.append(f'bpd."{pay_col}" > 0')

        where = ' WHERE ' + ' AND '.join(conditions) if conditions else ''
        
        return (f'SELECT bpd."district", bpd."designation", bpd."category", '
                f'bpd."{pay_col}" as "{pay_col}", bpd."class_type", bpd."fiscal_year" '
                f'FROM {bpd_table} bpd{where} '
                f'ORDER BY bpd."{pay_col}" DESC '
                f'LIMIT {top_k};')

    def _extract_district(self, text: str, ctx: SchemaContext) -> Optional[str]:
        text_lower = text.lower().strip().rstrip('?.,!')
        for d in ctx.metadata.get('districts', []):
            if d.lower() in text_lower:
                return d
        return None

    def _extract_designation(self, text: str, ctx: SchemaContext) -> Optional[str]:
        text_lower = text.lower().strip().rstrip('?.,!')
        designations_mr = ctx.metadata.get('designations_mr', {})
        for mr, en in designations_mr.items():
            if mr in text:
                return en
        for d in ctx.metadata.get('designations', []):
            if d.lower() in text_lower or text_lower in d.lower():
                return d
        return None


class SemanticCache:
    def __init__(self, maxsize: int = 500, ttl: int = 3600):
        from ..cache import TTLCache
        self._cache = TTLCache(maxsize=maxsize, ttl=ttl)
        self._key_map: Dict[str, str] = {}

    def _normalize(self, question: str) -> str:
        q = question.lower().strip()
        q = re.sub(r'\s+', ' ', q)
        q = re.sub(r'[?.,!;:]', '', q)
        return q

    def _hash(self, question: str, sub_scheme_code: str) -> str:
        normalized = self._normalize(question)
        return hashlib.md5(f"{sub_scheme_code}:{normalized}".encode()).hexdigest()

    def get(self, question: str, sub_scheme_code: str) -> Optional[str]:
        key = self._hash(question, sub_scheme_code)
        return self._cache.get(key)

    def put(self, question: str, sub_scheme_code: str, response: str):
        key = self._hash(question, sub_scheme_code)
        self._cache.put(key, response)

    def clear(self):
        self._cache.clear()


query_classifier = QueryClassifier()
fast_path_engine = FastPathEngine()
semantic_cache = SemanticCache(maxsize=500, ttl=1800)
