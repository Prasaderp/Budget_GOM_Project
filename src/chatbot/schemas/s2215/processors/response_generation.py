"""Response generation for 2215 schemes - district/account-head expenditure data."""
import json
from typing import Any

from langchain_core.output_parsers import StrOutputParser

from ....llm import _init_llm
from ..prompts.response_prompt import RESPONSE_PROMPT


def _format_numeric(value: Any) -> Any:
    """Format numeric-looking strings with commas; leave others unchanged."""
    if isinstance(value, str) and value.replace(",", "").replace(".", "").isdigit():
        try:
            numeric_value = float(value.replace(",", ""))
            if numeric_value.is_integer():
                return f"{numeric_value:,.0f}"
            return f"{numeric_value:,.2f}"
        except Exception:
            return value
    return value


def _collect_numeric_columns(results: list[dict[str, Any]]) -> dict[str, list[float]]:
    """Collect numeric columns relevant for 2215 (expenditure/budget/revised)."""
    numeric_cols: dict[str, list[float]] = {}
    for row in results:
        for key, value in row.items():
            key_lower = key.lower()
            if not (
                key_lower.startswith("expenditure_")
                or key_lower.startswith("budget_estimate_")
                or key_lower.startswith("revised_demand_")
            ):
                continue
            try:
                numeric_value = float(str(value).replace(",", "")) if value is not None else 0.0
            except Exception:
                continue
            numeric_cols.setdefault(key, []).append(numeric_value)
    return numeric_cols


def generate_response(question: str, results: Any) -> str:
    """Generate natural-language response for 2215 chatbot queries."""
    llm = _init_llm()

    if isinstance(results, str):
        results_str = results
    elif not results:
        results_str = "NO_RECORDS_FOUND"
    elif isinstance(results, list) and results:
        # Format up to a reasonable number of rows for the LLM.
        max_rows = min(20, len(results))
        sample = results[:max_rows]

        if isinstance(sample[0], dict):
            formatted_results: list[dict[str, Any]] = []
            for row in sample:
                formatted_row = {k: _format_numeric(v) for k, v in row.items()}
                formatted_results.append(formatted_row)

            results_str = json.dumps(formatted_results, indent=2, ensure_ascii=False)
            if len(results) > max_rows:
                results_str += f"\n... (showing {max_rows} of {len(results)} total records)"

            # Attach simple summary statistics across key numeric columns.
            try:
                numeric_cols = _collect_numeric_columns(results)
                total_records = len(results)
                if numeric_cols:
                    results_str += "\n\n=== SUMMARY STATISTICS ==="
                    for col, values in numeric_cols.items():
                        if not values:
                            continue
                        total_val = sum(values)
                        avg_val = total_val / len(values)
                        max_val = max(values)
                        min_val = min(values)
                        results_str += (
                            f"\n{col}: Total = ₹{total_val:,.0f}, "
                            f"Average = ₹{avg_val:,.0f}, "
                            f"Range = ₹{min_val:,.0f} - ₹{max_val:,.0f}"
                        )
                    results_str += f"\n\nTotal Records Analyzed: {total_records}"
            except Exception:
                results_str += "\n\n(Summary statistics unavailable)"
        else:
            # Non-dict rows: show a small sample only.
            results_str = str(sample)
            if len(results) > max_rows:
                results_str += f"\n... (showing first {max_rows} of {len(results)} results)"
    else:
        results_str = "NO_RECORDS_FOUND"

    try:
        response_chain = RESPONSE_PROMPT | llm | StrOutputParser()
        final_response = response_chain.invoke(
            {
                "question": question,
                "results": results_str,
            }
        )
        return final_response.strip()
    except Exception:
        return (
            "I apologize, but I'm having trouble formulating a response for this query. "
            "Please try rephrasing your question."
        )


