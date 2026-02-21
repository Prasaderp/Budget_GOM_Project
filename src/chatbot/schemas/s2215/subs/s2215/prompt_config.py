from dataclasses import dataclass
from typing import Optional, Dict

@dataclass
class PromptConfig:
    custom_context: Optional[Dict[str, str]] = None
    table_names: Optional[Dict[str, str]] = None

PROMPT_CONFIG = PromptConfig()
