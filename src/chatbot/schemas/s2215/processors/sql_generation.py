"""SQL generation for 2215 schemes - builds SQL chain with 2215-specific prompts."""
from typing import Optional

from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

from ....cache import TTLCache
from ....database import format_table_info_for_prompt, get_schema_info
from ....llm import _init_llm
from ...prompt_registry import subschema_prompt_registry
from ..prompts.sql_prompt import SQL_PROMPT

_built_prompt_cache = TTLCache(maxsize=50, ttl=7200)


def create_sql_chain(sub_scheme_code: Optional[str] = None):
    """Create SQL generation chain with 2215-specific prompts."""
    llm = _init_llm()
    schema_info = get_schema_info()
    table_info = format_table_info_for_prompt(schema_info, sub_scheme_code)

    # Build prompt with caching
    cache_key = f"prompt:{sub_scheme_code or 'default'}"
    cached_prompt = _built_prompt_cache.get(cache_key)

    if cached_prompt:
        sql_prompt = cached_prompt
    else:
        # Base context defaults if no subschema config is available.
        context = {
            "data_relationships": "No schema context available.",
            "common_patterns": "Use exact district names, fiscal years, and account_head_code values from the schema.",
            "examples": "No examples available.",
        }

        prompt_config = None
        if sub_scheme_code:
            prompt_config = subschema_prompt_registry.get_config(sub_scheme_code)

        if prompt_config and getattr(prompt_config, "custom_context", None):
            custom = prompt_config.custom_context
            if "data_relationships" in custom:
                context["data_relationships"] = custom["data_relationships"]
            if "common_patterns" in custom:
                context["common_patterns"] = custom["common_patterns"]
            if "examples" in custom:
                context["examples"] = custom["examples"]

        sql_prompt = SQL_PROMPT.partial(**context)
        _built_prompt_cache.put(cache_key, sql_prompt)

    sql_chain = (
        {
            "input": RunnablePassthrough(),
            "top_k": RunnablePassthrough(),
            "table_info": RunnablePassthrough(),
        }
        | sql_prompt
        | llm
        | StrOutputParser()
    )

    return sql_chain, table_info


