from typing import Any
from langchain_core.output_parsers import StrOutputParser
from ....llm import _init_llm
from ....core.response_synthesizer import response_synthesizer
from ..prompts.response_prompt import RESPONSE_PROMPT


def generate_response(question: str, results: Any) -> str:
    template = response_synthesizer.template_response(question, results)
    if template is not None:
        return template

    if not response_synthesizer.needs_llm(results):
        template = response_synthesizer.template_response(question, results)
        if template:
            return template

    compressed = response_synthesizer.compress_results_for_llm(results, question)

    try:
        llm = _init_llm()
        chain = RESPONSE_PROMPT | llm | StrOutputParser()
        return chain.invoke({"question": question, "results": compressed}).strip()
    except Exception:
        return "I apologize, but I'm having trouble formulating a response. Please try rephrasing your question."
