import json
import re
from typing import Any, List, Dict, Optional


class ResponseSynthesizer:
    _SIMPLE_THRESHOLD = 3
    _SKIP_FIELDS = {'id', 'scheme_code', 'sub_scheme_code'}

    _RELATIVE_COL_RE = re.compile(
        r'^(expenditure|budget|forecast|sanctioned_posts|revised_grant|budget_grant'
        r'|budget_estimate|revised_estimate|filled_posts|vacant_posts'
        r'|basic_pay|grade_pay|special_pay|allowance|hra_rate'
        r'|medical_expenses|festival_advance|nps|swagram_maharashtra_darshan'
        r'|actual_receipts|budget_receipts|revised_receipts'
        r'|sub_head_expenditure|account_head_expenditure)'
        r'_(prev\d+|curr(?:_[a-z_]+)?)$'
    )

    _PREFIX_LABELS = {
        'expenditure': 'Expenditure',
        'budget': 'Budget',
        'forecast': 'Forecast',
        'sanctioned_posts': 'Sanctioned Posts',
        'revised_grant': 'Revised Grant',
        'budget_grant': 'Budget Grant',
        'budget_estimate': 'Budget Estimate',
        'revised_estimate': 'Revised Estimate',
        'filled_posts': 'Filled Posts',
        'vacant_posts': 'Vacant Posts',
        'basic_pay': 'Basic Pay',
        'grade_pay': 'Grade Pay',
        'special_pay': 'Special Pay',
        'allowance': 'Allowance',
        'hra_rate': 'HRA Rate',
        'medical_expenses': 'Medical Expenses',
        'festival_advance': 'Festival Advance',
        'nps': 'NPS',
        'swagram_maharashtra_darshan': 'Swagram Maharashtra Darshan',
        'actual_receipts': 'Actual Receipts',
        'budget_receipts': 'Budget Receipts',
        'revised_receipts': 'Revised Receipts',
        'sub_head_expenditure': 'Sub Head Expenditure',
        'account_head_expenditure': 'Account Head Expenditure',
    }

    _CURR_QUALIFIER_LABELS = {
        'estimating_officer': '(Estimating Officer)',
        'controlling_officer': '(Controlling Officer)',
        'admin_dept': '(Admin Dept)',
        'finance_dept': '(Finance Dept)',
    }

    def _fiscal_year_for_offset(self, base_fy: str, offset: int) -> str:
        try:
            start = int(base_fy.split('-')[0])
        except (ValueError, IndexError, AttributeError):
            return ''
        target = start + offset
        return f"{target}-{str(target + 1)[2:]}"

    def _resolve_column_label(self, col_name: str, fiscal_year: str) -> str:
        m = self._RELATIVE_COL_RE.match(col_name)
        if not m:
            label = col_name.replace('_', ' ').title()
            if col_name == 'fiscal_year':
                return 'Fiscal Year'
            return label

        prefix = m.group(1)
        suffix = m.group(2)
        prefix_label = self._PREFIX_LABELS.get(prefix, prefix.replace('_', ' ').title())

        if suffix.startswith('prev'):
            try:
                n = int(suffix[4:])
            except ValueError:
                return f"{prefix_label} {suffix}"
            fy_str = self._fiscal_year_for_offset(fiscal_year, -n)
            return f"{prefix_label} {fy_str}" if fy_str else f"{prefix_label} {suffix}"

        if suffix == 'curr':
            fy_str = self._fiscal_year_for_offset(fiscal_year, 0)
            return f"{prefix_label} {fy_str}" if fy_str else f"{prefix_label} Current"

        if suffix.startswith('curr_'):
            qualifier_key = suffix[5:]
            qualifier = self._CURR_QUALIFIER_LABELS.get(qualifier_key, qualifier_key.replace('_', ' ').title())
            fy_str = self._fiscal_year_for_offset(fiscal_year, 0)
            year_part = f" {fy_str}" if fy_str else ""
            return f"{prefix_label}{year_part} {qualifier}"

        return f"{prefix_label} {suffix}"

    def _extract_fiscal_year_from_rows(self, rows: List[Dict]) -> str:
        for row in rows:
            fy = row.get('fiscal_year', '')
            if fy and '-' in str(fy):
                return str(fy).strip()
        return ''

    def needs_llm(self, results: Any) -> bool:
        if isinstance(results, str):
            return True
        if isinstance(results, list):
            if len(results) <= self._SIMPLE_THRESHOLD:
                return False
            return True
        return True

    def template_response(self, question: str, results: Any) -> Optional[str]:
        if isinstance(results, str):
            return self._handle_string_result(question, results)
        if not isinstance(results, list) or not results:
            return None
        if len(results) > self._SIMPLE_THRESHOLD:
            return None
        return self._format_simple_results(question, results)

    def _handle_string_result(self, question: str, result: str) -> Optional[str]:
        if result == "UNRELATED_QUERY_ATTEMPT":
            return ("This system provides information about government budget allocations, "
                    "staffing details, post expenses, and unit expenditures only.")
        if result == "NO_RECORDS_FOUND":
            return ("No information found matching the specified criteria. "
                    "Please verify district names, designations, categories, or time periods.")
        if result.startswith("DATABASE_ERROR"):
            return "Technical difficulties accessing the budget information. Please try again."
        if result.startswith("GENERAL_ERROR"):
            return "An error occurred while processing your request. Please try again."
        if result.startswith("SQL_VALIDATION_ERROR"):
            return "The query could not be validated for security reasons."
        if result.startswith("SECURITY_POLICY"):
            return result.replace("SECURITY_POLICY: ", "")
        return None

    def _format_simple_results(self, question: str, results: List[Dict]) -> str:
        if len(results) == 1:
            return self._format_single_row(question, results[0])
        fy = self._extract_fiscal_year_from_rows(results)
        lines = []
        for row in results:
            row_fy = str(row.get('fiscal_year', '')).strip() or fy
            parts = []
            for k, v in row.items():
                if k in self._SKIP_FIELDS:
                    continue
                label = self._resolve_column_label(k, row_fy)
                parts.append(f"**{label}**: {self._fmt_val(k, v)}")
            lines.append(" | ".join(parts))
        return "\n".join(lines)

    def _format_single_row(self, question: str, row: Dict) -> str:
        fy = str(row.get('fiscal_year', '')).strip()
        parts = []
        for k, v in row.items():
            if k in self._SKIP_FIELDS:
                continue
            label = self._resolve_column_label(k, fy)
            parts.append(f"**{label}**: {self._fmt_val(k, v)}")
        return " | ".join(parts)

    def _fmt_val(self, key: str, val: str) -> str:
        money_keys = ('pay', 'salary', 'expenditure', 'budget', 'forecast', 'expenses',
                      'allowance', 'advance', 'nps', 'other', 'total', 'medical',
                      'festival', 'swagram', 'commission', 'dearness', 'house_rent',
                      'travel', 'grade_pay', 'special_pay', 'actual', 'revised',
                      'estimate', 'revenue', 'receipt')
        if any(mk in key.lower() for mk in money_keys):
            try:
                num = float(str(val).replace(',', ''))
                return f"₹{num:,.0f}" if num == int(num) else f"₹{num:,.2f}"
            except (ValueError, AttributeError):
                pass
        return str(val)

    def compress_results_for_llm(self, results: Any, question: str, max_rows: int = 20) -> str:
        if isinstance(results, str):
            return results
        if not isinstance(results, list) or not results:
            return "NO_RECORDS_FOUND"

        fy = self._extract_fiscal_year_from_rows(results)

        is_division = any(d in question.lower() for d in ['division', 'all districts'])
        cap = min(80 if is_division else max_rows, len(results))

        formatted = []
        for row in results[:cap]:
            clean = {}
            row_fy = str(row.get('fiscal_year', '')).strip() or fy
            for k, v in row.items():
                if k in ('id', 'scheme_code', 'sub_scheme_code'):
                    continue
                resolved = self._resolve_column_label(k, row_fy)
                clean[resolved] = v
            formatted.append(clean)

        output = json.dumps(formatted, indent=1, ensure_ascii=False)
        if len(results) > cap:
            output += f"\n... ({cap} of {len(results)} records shown)"

        numeric_cols = {}
        for row in results:
            row_fy = str(row.get('fiscal_year', '')).strip() or fy
            for k, v in row.items():
                if k in ('id', 'scheme_code', 'sub_scheme_code', 'fiscal_year', 'district',
                          'designation', 'category', 'class_type', 'unit_account', 'status',
                          'hra_rate'):
                    continue
                try:
                    num = float(str(v).replace(',', ''))
                except (ValueError, TypeError):
                    continue
                resolved = self._resolve_column_label(k, row_fy)
                numeric_cols.setdefault(resolved, []).append(num)

        if numeric_cols:
            output += "\n\n=== SUMMARY ==="
            for col, vals in numeric_cols.items():
                total = sum(vals)
                output += f"\n{col}: Total={total:,.0f}, Avg={total/len(vals):,.0f}, Count={len(vals)}"

        return output


response_synthesizer = ResponseSynthesizer()
