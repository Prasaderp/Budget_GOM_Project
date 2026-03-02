import re
from typing import Dict, List, Optional, Tuple
from ..cache import TTLCache
from ..database import get_schema_info, get_db_connection, return_db_connection
from src.core.registry import scheme_registry
from src.core.base_config import BaseSchemeConfig

_schema_context_cache = TTLCache(maxsize=50, ttl=7200)
_fiscal_year_cache = TTLCache(maxsize=50, ttl=3600)


class SchemaContext:
    def __init__(self, tables: Dict[str, Dict], fiscal_column_map: Dict[str, List[str]],
                 metadata: Dict, table_names: Dict[str, str],
                 available_fiscal_years: List[str] = None,
                 default_fiscal_year: str = ""):
        self.tables = tables
        self.fiscal_column_map = fiscal_column_map
        self.metadata = metadata
        self.table_names = table_names
        self.available_fiscal_years = available_fiscal_years or []
        self.default_fiscal_year = default_fiscal_year
        self.all_columns = {}
        for tname, tinfo in tables.items():
            self.all_columns[tname] = [col['column_name'] for col in tinfo.get('columns', [])]

    def get_table_for_keyword(self, keyword: str) -> Optional[str]:
        kw = keyword.lower()
        mapping = {
            'basic_pay': 'budget_post_details', 'designation': 'budget_post_details',
            'sanctioned_posts': 'budget_post_details', 'grade_pay': 'budget_post_details',
            'special_pay': 'budget_post_details', 'allowance': 'budget_post_details',
            'hra_rate': 'budget_post_details',
            'filled': 'post_expenses', 'vacant': 'post_expenses',
            'medical': 'post_expenses', 'festival': 'post_expenses',
            'nps': 'post_expenses', 'commission': 'post_expenses',
            'swagram': 'post_expenses',
            'salary': 'post_status', 'status': 'post_status',
            'dearness': 'post_status', 'house_rent': 'post_status',
            'expenditure': 'unit_expenditure', 'budget': 'unit_expenditure',
            'forecast': 'unit_expenditure', 'unit_account': 'unit_expenditure',
            'sub_head': 'sub_head_expenditure', 'pension': 'sub_head_expenditure',
            'account_head': 'district_expenditure', 'water': 'district_expenditure',
            'scarcity': 'district_expenditure', 'flood': 'district_expenditure',
            'cyclone': 'district_expenditure', 'drought': 'district_expenditure',
            'calamity': 'district_expenditure', 'loan': 'district_expenditure',
            'crop': 'district_expenditure', 'advance': 'district_expenditure',
            'welfare': 'district_expenditure',
            'revenue': 'district_revenue', 'receipt': 'district_revenue',
            'land_revenue': 'district_revenue',
        }
        for k, v in mapping.items():
            if k in kw:
                return self.table_names.get(v)
        return None

    def column_exists(self, table_name: str, column_name: str) -> bool:
        return column_name in self.all_columns.get(table_name, [])

    def has_fiscal_year_column(self) -> bool:
        """Check if any table has a fiscal_year column."""
        for cols in self.all_columns.values():
            if 'fiscal_year' in cols:
                return True
        return False


class DynamicSchemaEngine:
    _FY_COL_PATTERN = re.compile(r'^(.+?)_(\d{4})_(\d{2})$')
    _TABLE_ALIASES = {
        'budget_post_details': 'bpd',
        'post_status': 'ps',
        'post_expenses': 'pe',
        'unit_expenditure': 'ue',
        'sub_head_expenditure': 'she',
        'district_expenditure': 'de',
        'district_revenue': 'dr',
    }

    def build_context(self, sub_scheme_code: str) -> SchemaContext:
        cache_key = f"ctx:{sub_scheme_code}"
        cached = _schema_context_cache.get(cache_key)
        if cached:
            return cached

        config = scheme_registry.get_scheme(sub_scheme_code)
        if not config:
            raise ValueError(f"Scheme {sub_scheme_code} not found in registry")

        schema_info = get_schema_info()
        table_names = self._resolve_table_names(config)
        relevant_tables = {tn: schema_info[tn] for tn in table_names.values() if tn in schema_info}
        fiscal_map = self._classify_fiscal_columns(relevant_tables)
        metadata = self._extract_metadata(config)

        # Discover available fiscal years from the database
        available_fy, default_fy = self._discover_fiscal_years(table_names)

        ctx = SchemaContext(
            tables=relevant_tables,
            fiscal_column_map=fiscal_map,
            metadata=metadata,
            table_names=table_names,
            available_fiscal_years=available_fy,
            default_fiscal_year=default_fy,
        )
        _schema_context_cache.put(cache_key, ctx)
        return ctx

    def _discover_fiscal_years(self, table_names: Dict[str, str]) -> Tuple[List[str], str]:
        """Discover available fiscal years from the actual database data.
        Returns (sorted list of fiscal years, default fiscal year).
        """
        # Pick any table to check fiscal_year values
        target_table = None
        for tname in table_names.values():
            if tname:
                target_table = tname
                break
        if not target_table:
            return [], ""

        fy_cache_key = f"fy:{target_table}"
        cached = _fiscal_year_cache.get(fy_cache_key)
        if cached:
            return cached

        conn = None
        try:
            conn = get_db_connection(timeout=5)
            cur = conn.cursor()
            # Check if fiscal_year column exists
            cur.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_schema='public' AND table_name=%s AND column_name='fiscal_year'
            """, (target_table,))
            if not cur.fetchone():
                result = ([], "")
                _fiscal_year_cache.put(fy_cache_key, result)
                return result

            cur.execute(f'SELECT DISTINCT "fiscal_year" FROM "{target_table}" ORDER BY "fiscal_year"')
            fiscal_years = [row[0].strip() for row in cur.fetchall() if row[0]]
            cur.close()

            # Default to the first (earliest) fiscal year as it represents the "current" budget year
            # In government budgeting, the earliest FY is typically the active one
            default_fy = fiscal_years[0] if fiscal_years else ""

            result = (fiscal_years, default_fy)
            _fiscal_year_cache.put(fy_cache_key, result)
            return result
        except Exception as e:
            print(f"Error discovering fiscal years: {e}")
            return [], ""
        finally:
            return_db_connection(conn)

    def _resolve_table_names(self, config: BaseSchemeConfig) -> Dict[str, str]:
        names = {}
        for form_name, form_config in config.forms.items():
            if form_config.table_name:
                names[form_name] = form_config.table_name
        return names

    def _classify_fiscal_columns(self, tables: Dict[str, Dict]) -> Dict[str, List[str]]:
        result = {}
        for tname, tinfo in tables.items():
            for col in tinfo.get('columns', []):
                m = self._FY_COL_PATTERN.match(col['column_name'])
                if m:
                    key = m.group(1)  # e.g. 'expenditure', 'budget_grant', 'revised_grant'
                    if key not in result:
                        result[key] = []
                    result[key].append(col['column_name'])
        return result

    def _extract_metadata(self, config: BaseSchemeConfig) -> Dict:
        return {
            'districts': config.districts or [],
            'designations': config.designations,
            'designations_mr': config.designations_mr,
            'categories': config.categories,
            'categories_mr': config.categories_mr,
            'classes': config.classes,
            'classes_mr': config.classes_mr,
            'primary_units': config.primary_units,
            'primary_units_mr': config.primary_units_mr,
            'scheme_name': config.name_en,
        }

    def format_selective_table_info(self, ctx: SchemaContext,
                                     target_tables: Optional[List[str]] = None) -> str:
        tables_to_format = target_tables or list(ctx.tables.keys())
        lines = []
        for tname in tables_to_format:
            if tname not in ctx.tables:
                continue
            tinfo = ctx.tables[tname]
            form_key = None
            for fk, tn in ctx.table_names.items():
                if tn == tname:
                    form_key = fk
                    break
            alias = self._TABLE_ALIASES.get(form_key, tname[:3])
            lines.append(f"=== TABLE: {tname} (alias: {alias}) ===")
            key_cols, other_cols = [], []
            for col in tinfo.get('columns', []):
                col_type = col['data_type']
                if col.get('character_maximum_length'):
                    col_type += f"({col['character_maximum_length']})"
                nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                info = f'"{col["column_name"]}" {col_type} {nullable}'
                if col['column_name'] in ('district', 'category', 'designation', 'class_type',
                                           'unit_account', 'status', 'fiscal_year',
                                           'account_head_code', 'sub_head', 'remarks',
                                           'table_section_code'):
                    key_cols.append(info)
                else:
                    other_cols.append(info)
            if key_cols:
                lines.append("Key Columns: " + ', '.join(key_cols))
            if other_cols:
                lines.append("Other Columns: " + ', '.join(other_cols))
            lines.append("")
        return "\n".join(lines)

    _TABLE_KEYWORDS = {
        'budget_post_details': ['basic pay', 'designation', 'sanctioned', 'posts', 'grade pay',
                                'special pay', 'allowance', 'hra'],
        'post_status': ['salary', 'status', 'dearness', 'house rent', 'travel'],
        'post_expenses': ['medical', 'festival', 'swagram', 'nps', 'commission',
                          'filled', 'vacant', 'filled_posts', 'vacant_posts'],
        'unit_expenditure': ['unit account', 'unit_account'],
        'sub_head_expenditure': ['sub head', 'sub_head', 'pension'],
        'district_expenditure': ['expenditure', 'budget', 'forecast', 'account head',
                                 'scarcity', 'water', 'flood', 'cyclone', 'drought',
                                 'calamity', 'loan', 'crop', 'advance', 'welfare',
                                 'revised', 'estimate', 'grant'],
        'district_revenue': ['revenue', 'receipt', 'actual', 'land revenue'],
    }

    def detect_relevant_tables(self, question: str, ctx: SchemaContext) -> List[str]:
        q = question.lower()
        tables = []
        for form_key, keywords in self._TABLE_KEYWORDS.items():
            actual_table = ctx.table_names.get(form_key)
            if actual_table and any(k in q for k in keywords):
                tables.append(actual_table)
        if not tables:
            tables = [t for t in ctx.table_names.values() if t]
        return tables


schema_engine = DynamicSchemaEngine()
