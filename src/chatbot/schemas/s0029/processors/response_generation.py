"""Response generation for 0029 - formats land revenue data with bilingual support"""
import json
from typing import Any
from langchain_core.output_parsers import StrOutputParser
from ....llm import _init_llm
from ..prompts.response_prompt import RESPONSE_PROMPT

def generate_response(question: str, results: Any) -> str:
    """
    Generate natural language response from SQL results for 0029.
    
    Logic: Format with Indian currency, summaries, historical context
    """
    llm = _init_llm()

    # Handle different result types
    if isinstance(results, str):
        results_str = results
    elif not results:
        results_str = "NO_RECORDS_FOUND"
    elif isinstance(results, list) and len(results) > 0:
        if isinstance(results[0], dict):
            # Limit results for prompt efficiency (max 20 rows)
            max_results = min(20, len(results))
            
            # Format numeric values with Indian currency notation
            formatted_results = []
            for result in results[:max_results]:
                formatted_result = {}
                for key, value in result.items():
                    # Detect numeric fields and format with commas
                    if isinstance(value, (int, float)):
                        formatted_result[key] = f"{value:,.0f}" if isinstance(value, int) else f"{value:,.2f}"
                    elif isinstance(value, str) and value.replace(',', '').replace('.', '').isdigit():
                        try:
                            numeric_value = float(value.replace(',', ''))
                            formatted_result[key] = f"{numeric_value:,.0f}" if numeric_value.is_integer() else f"{numeric_value:,.2f}"
                        except:
                            formatted_result[key] = value
                    else:
                        formatted_result[key] = value
                formatted_results.append(formatted_result)
            
            results_str = json.dumps(formatted_results, indent=2, ensure_ascii=False)

            if len(results) > max_results:
                results_str += f"\n... (showing {max_results} of {len(results)} total records)"

            # Generate summary statistics for revenue/budget columns
            try:
                numeric_cols = {}
                for result in results:
                    for key, value in result.items():
                        # Match revenue and budget columns
                        if any(term in key.lower() for term in ['actual', 'budget', 'estimate', 'revised', 'deposit', 'reconciliation']):
                            try:
                                numeric_value = float(str(value).replace(',', '')) if value else 0
                                if key not in numeric_cols:
                                    numeric_cols[key] = []
                                numeric_cols[key].append(numeric_value)
                            except:
                                continue

                if numeric_cols:
                    results_str += "\n\n=== SUMMARY STATISTICS ==="
                    for col, values in numeric_cols.items():
                        if values:
                            total = sum(values)
                            avg = total / len(values)
                            results_str += f"\n{col}: Total = ₹{total:,.0f}, Average = ₹{avg:,.0f}"
                    results_str += f"\n\nTotal Records: {len(results)}"
            except:
                pass  # Skip summary if any error
        else:
            # Non-dict results (simple values)
            results_str = str(results[:8])
            if len(results) > 8:
                results_str += f"\n... (showing first 8 of {len(results)} results)"
    else:
        results_str = "NO_RECORDS_FOUND"

    # Generate conversational response using LLM
    try:
        response_chain = RESPONSE_PROMPT | llm | StrOutputParser()
        final_response = response_chain.invoke({
            "question": question,
            "results": results_str
        })
        return final_response.strip()
    except Exception as e:
        print(f"Error generating response: {e}")
        return "I apologize, but I'm having trouble formulating a response. Please try rephrasing your question."
