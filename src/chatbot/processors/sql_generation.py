from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from ..llm import _init_llm
from ..database import get_schema_info, format_table_info_for_prompt
from ..prompts import SQL_PROMPT

def create_sql_chain():
    llm = _init_llm()
    schema_info = get_schema_info()
    table_info = format_table_info_for_prompt(schema_info)

    sql_chain = (
        {"input": RunnablePassthrough(), "top_k": RunnablePassthrough(), "table_info": RunnablePassthrough()}
        | SQL_PROMPT
        | llm
        | StrOutputParser()
    )

    return sql_chain, table_info
