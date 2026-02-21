import json
from typing import Any, List, Dict, Optional
from .schema_engine import SchemaContext


class ResponseSynthesizer:
    _SIMPLE_THRESHOLD = 3
    # Fields to skip entirely in formatted output
    _SKIP_FIELDS = {'id', 'scheme_code', 'sub_scheme_code'}

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
        lines = []
        for row in results:
            parts = []
            for k, v in row.items():
                if k in self._SKIP_FIELDS:
                    continue
                label = k.replace('_', ' ').title()
                if k == 'fiscal_year':
                    label = 'Fiscal Year'
                parts.append(f"**{label}**: {self._fmt_val(k, v)}")
            lines.append(" | ".join(parts))
        return "\n".join(lines)

    def _format_single_row(self, question: str, row: Dict) -> str:
        parts = []
        for k, v in row.items():
            if k in self._SKIP_FIELDS:
                continue
            label = k.replace('_', ' ').title()
            if k == 'fiscal_year':
                label = 'Fiscal Year'
            parts.append(f"**{label}**: {self._fmt_val(k, v)}")
        return " | ".join(parts)

    def _fmt_val(self, key: str, val: str) -> str:
        money_keys = ('pay', 'salary', 'expenditure', 'budget', 'forecast', 'expenses',
                      'allowance', 'advance', 'nps', 'other', 'total', 'medical',
                      'festival', 'swagram', 'commission', 'dearness', 'house_rent',
                      'travel', 'grade_pay', 'special_pay')
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

        is_division = any(d in question.lower() for d in ['division', 'all districts'])
        cap = min(80 if is_division else max_rows, len(results))

        formatted = []
        for row in results[:cap]:
            clean = {}
            for k, v in row.items():
                if k in ('id', 'scheme_code', 'sub_scheme_code'):
                    continue
                clean[k] = v
            formatted.append(clean)

        output = json.dumps(formatted, indent=1, ensure_ascii=False)
        if len(results) > cap:
            output += f"\n... ({cap} of {len(results)} records shown)"

        numeric_cols = {}
        for row in results:
            for k, v in row.items():
                if k in ('id', 'scheme_code', 'sub_scheme_code', 'fiscal_year', 'district',
                          'designation', 'category', 'class_type', 'unit_account', 'status',
                          'hra_rate'):
                    continue
                try:
                    num = float(str(v).replace(',', ''))
                except (ValueError, TypeError):
                    continue
                numeric_cols.setdefault(k, []).append(num)

        if numeric_cols:
            output += "\n\n=== SUMMARY ==="
            for col, vals in numeric_cols.items():
                total = sum(vals)
                output += f"\n{col}: Total={total:,.0f}, Avg={total/len(vals):,.0f}, Count={len(vals)}"

        return output


response_synthesizer = ResponseSynthesizer()
