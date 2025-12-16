"""Response generation for 2053 schemes - handles district, post, and expenditure data"""
import json
from typing import Any
from langchain_core.output_parsers import StrOutputParser
from ....llm import _init_llm
from ..prompts.response_prompt import RESPONSE_PROMPT

def generate_response(question: str, results: Any) -> str:
    llm = _init_llm()

    if isinstance(results, str):
        results_str = results
    elif not results:
        results_str = "NO_RECORDS_FOUND"
    elif isinstance(results, list) and len(results) > 0:
        if isinstance(results[0], dict):
            is_division_query = any(division in question.lower() for division in ['konkan division', 'mumbai division', 'division'])
            max_results_for_prompt = min(98 if is_division_query else 15, len(results))
            
            formatted_results = []
            for i, result in enumerate(results[:max_results_for_prompt]):
                formatted_result = {}
                for key, value in result.items():
                    if isinstance(value, str) and value.replace(',', '').replace('.', '').isdigit():
                        try:
                            numeric_value = float(value.replace(',', ''))
                            formatted_result[key] = f"{numeric_value:,.0f}" if numeric_value.is_integer() else f"{numeric_value:,.2f}"
                        except:
                            formatted_result[key] = value
                    else:
                        formatted_result[key] = value
                formatted_results.append(formatted_result)
            
            results_str = json.dumps(formatted_results, indent=2, ensure_ascii=False)

            if len(results) > max_results_for_prompt:
                results_str += f"\n... (showing {max_results_for_prompt} of {len(results)} total records)"

            try:
                numeric_cols = {}
                total_records = len(results)
                
                for result in results:
                    for key, value in result.items():
                        if key.lower() in ['basic_pay', 'grade_pay', 'salary', 'expenditure', 'budget', 'filled_posts', 'vacant_posts', 'sanctioned_posts']:
                            try:
                                numeric_value = float(str(value).replace(',', '')) if value else 0
                                if key not in numeric_cols:
                                    numeric_cols[key] = []
                                numeric_cols[key].append(numeric_value)
                            except:
                                continue

                if numeric_cols and len(numeric_cols) > 0:
                    results_str += "\n\n=== SUMMARY STATISTICS ==="
                    for col, values in numeric_cols.items():
                        if values and len(values) > 0:
                            total_val = sum(values)
                            avg_val = total_val / len(values)
                            max_val = max(values)
                            min_val = min(values)
                            
                            if 'post' in col.lower():
                                results_str += f"\n{col}: Total = {total_val:,.0f}, Average = {avg_val:,.1f}, Range = {min_val:,.0f} - {max_val:,.0f}"
                            else:
                                results_str += f"\n{col}: Total = ₹{total_val:,.0f}, Average = ₹{avg_val:,.0f}, Range = ₹{min_val:,.0f} - ₹{max_val:,.0f}"
                    
                    results_str += f"\n\nTotal Records Analyzed: {total_records}"
            except Exception as e:
                results_str += "\n\n(Summary statistics unavailable)"
        else:
            results_str = str(results[:8])
            if len(results) > 8:
                results_str += f"\n... (showing first 8 of {len(results)} results)"
    else:
        results_str = "NO_RECORDS_FOUND"

    try:
        response_chain = RESPONSE_PROMPT | llm | StrOutputParser()
        final_response = response_chain.invoke({
            "question": question,
            "results": results_str
        })
        return final_response.strip()
    except Exception as e:
        print(f"Error generating final response with LLM: {e}")
        return "I apologize, but I'm having trouble formulating a response. Please try rephrasing your question."

