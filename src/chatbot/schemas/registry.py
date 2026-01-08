"""Registry for routing subscheme codes to their main scheme processors"""
import importlib
from typing import Optional, Tuple, Any
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import ModuleType

class ChatbotSchemaRegistry:
    """Routes subscheme codes to their main scheme processors and prompts"""
    
    _instance = None
    _scheme_cache: dict[str, Tuple[Any, Any]] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_scheme_code(self, sub_scheme_code: Optional[str]) -> Optional[str]:
        """Extract main scheme code from subscheme code (e.g., 20530028 → 2053, 20750249 → 2075)"""
        if not sub_scheme_code:
            return None
        
        if len(sub_scheme_code) >= 4:
            return sub_scheme_code[:4]
        
        return None
    
    def get_processors(self, sub_scheme_code: Optional[str]) -> Optional[Tuple[Any, Any, Any]]:
        """
        Dynamically import and return scheme-specific processors.
        Returns tuple: (preprocessing_module, sql_generation_module, response_generation_module)
        """
        scheme_code = self.get_scheme_code(sub_scheme_code)
        if not scheme_code:
            return None
        
        cache_key = f"{scheme_code}_processors"
        if cache_key in self._scheme_cache:
            return self._scheme_cache[cache_key]
        
        try:
            module_path = f"src.chatbot.schemas.s{scheme_code}.processors"
            processors_module = importlib.import_module(module_path)
            
            preprocessing = getattr(processors_module, 'preprocess_question', None)
            sql_generation = getattr(processors_module, 'create_sql_chain', None)
            response_generation = getattr(processors_module, 'generate_response', None)
            
            if preprocessing and sql_generation and response_generation:
                result = (preprocessing, sql_generation, response_generation)
                self._scheme_cache[cache_key] = result
                return result
        except (ImportError, AttributeError) as e:
            print(f"Error loading processors for scheme {scheme_code}: {e}")
        
        return None

# Global registry instance
chatbot_schema_registry = ChatbotSchemaRegistry()

