"""SQL generation for 7610 - unified schema across all 4 subschemes"""
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from typing import Optional
from ....llm import _init_llm
from ....database import get_schema_info, format_table_info_for_prompt
from ....cache import TTLCache
from ..context_generator import SchemaContextGenerator
from src.core.base_config import BaseSchemeConfig
from src.core.registry import scheme_registry
from ..prompts.sql_prompt import SQL_PROMPT

_built_prompt_cache = TTLCache(maxsize=50, ttl=7200)

def create_sql_chain(sub_scheme_code: Optional[str] = None):
    """Create SQL generation chain with subscheme-specific prompts"""
    llm = _init_llm()
    schema_info = get_schema_info()
    table_info = format_table_info_for_prompt(schema_info, sub_scheme_code)
    
    # Build prompt with caching - O(1) after first load
    cache_key = f"prompt_7610:{sub_scheme_code or 'default'}"
    cached_prompt = _built_prompt_cache.get(cache_key)
    
    if cached_prompt:
        sql_prompt = cached_prompt
    else:
        config: Optional[BaseSchemeConfig] = None
        if sub_scheme_code:
            config = scheme_registry.get_scheme(sub_scheme_code)
        
        if config:
            context = SchemaContextGenerator.generate_context(config)
        else:
            # Fallback context
            context = {
                'table_name': 'district_expenditure_7610',
                'data_relationships': 'Single table, 7 districts + DCO Staff',
                'common_patterns': 'Konkan districts + DCO',
                'examples': 'No examples available.'
            }
        
        sql_prompt = SQL_PROMPT.partial(**context)
        _built_prompt_cache.put(cache_key, sql_prompt)
    
    sql_chain = (
        {"input": RunnablePassthrough(), "top_k": RunnablePassthrough(), "table_info": RunnablePassthrough()}
        | sql_prompt
        | llm
        | StrOutputParser()
    )
    
    return sql_chain, table_info
