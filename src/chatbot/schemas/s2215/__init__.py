"""2215 (Water Scarcity) chatbot schema package."""
from . import processors, prompts
from .context_generator import SchemaContextGenerator

__all__ = ['processors', 'prompts', 'SchemaContextGenerator']
