from functools import lru_cache
from langchain_openai import ChatOpenAI
from .config import OPENAI_API_KEY

@lru_cache(maxsize=1)
def _init_llm() -> ChatOpenAI:
    try:
        print("Initializing OpenAI Chat LLM...")
        local_llm = ChatOpenAI(
            api_key=OPENAI_API_KEY,
            model="gpt-4o-mini",
            temperature=0.05,
            max_tokens=3000,
            request_timeout=45,
            top_p=0.85,
            frequency_penalty=0.15,
            presence_penalty=0.05,
        )
        print("OpenAI Chat LLM initialized successfully.")
        return local_llm
    except Exception as e:
        print(f"Error initializing OpenAI LLM: {e}")
        raise
