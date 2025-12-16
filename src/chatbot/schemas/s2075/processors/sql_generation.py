"""SQL generation for 2075 schemes - builds SQL chain with 2075-specific prompts"""
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from typing import Optional
from ....llm import _init_llm
from ....database import get_schema_info, format_table_info_for_prompt
from ....cache import TTLCache
from ...prompt_registry import subschema_prompt_registry
from src.core.registry import scheme_registry
from ..prompts.sql_prompt import SQL_PROMPT

_built_prompt_cache = TTLCache(maxsize=50, ttl=7200)

def create_sql_chain(sub_scheme_code: Optional[str] = None):
    """Create SQL generation chain with 2075-specific prompts"""
    llm = _init_llm()
    schema_info = get_schema_info()
    table_info = format_table_info_for_prompt(schema_info, sub_scheme_code)
    
    # Build prompt with caching
    cache_key = f"prompt:{sub_scheme_code or 'default'}"
    cached_prompt = _built_prompt_cache.get(cache_key)
    
    if cached_prompt:
        sql_prompt = cached_prompt
    else:
        # Get subschema-specific customizations
        prompt_config = None
        if sub_scheme_code:
            prompt_config = subschema_prompt_registry.get_config(sub_scheme_code)
        
        context = {
            'data_relationships': 'No schema context available.',
            'common_patterns': 'Use exact values from schema.',
            'examples': 'No examples available.'
        }
        
        if prompt_config:
            if prompt_config.custom_context:
                custom = prompt_config.custom_context
                if 'data_relationships' in custom:
                    context['data_relationships'] = custom['data_relationships']
                if 'common_patterns' in custom:
                    context['common_patterns'] = custom['common_patterns']
                if 'examples' in custom:
                    context['examples'] = custom['examples']
        
        sql_prompt = SQL_PROMPT.partial(**context)
        _built_prompt_cache.put(cache_key, sql_prompt)
    
    sql_chain = (
        {"input": RunnablePassthrough(), "top_k": RunnablePassthrough(), "table_info": RunnablePassthrough()}
        | sql_prompt
        | llm
        | StrOutputParser()
    )
    
    return sql_chain, table_info

