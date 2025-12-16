"""Subschema-specific prompt configurations registry"""
import importlib
import logging
from typing import Dict, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)

class SubschemaPromptRegistry:
    """Registry for subschema-specific prompt configurations"""
    
    _instance = None
    _configs: Dict[str, Any] = {}
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._configs = {}
        self._initialized = True
    
    def register_config(self, sub_scheme_code: str, config: Any) -> None:
        """Register a subschema prompt configuration"""
        self._configs[sub_scheme_code] = config
        logger.debug(f"Registered prompt config for subschema: {sub_scheme_code}")
    
    def get_config(self, sub_scheme_code: str) -> Optional[Any]:
        """Get prompt configuration for a subschema"""
        if sub_scheme_code in self._configs:
            return self._configs[sub_scheme_code]
        
        # Lazy load from new schemas structure
        scheme_code = sub_scheme_code[:4] if sub_scheme_code and len(sub_scheme_code) >= 4 else None
        
        if scheme_code:
            try:
                module_path = f"src.chatbot.schemas.s{scheme_code}.subs.{sub_scheme_code}.prompt_config"
                module = importlib.import_module(module_path)
                if hasattr(module, 'PROMPT_CONFIG'):
                    self.register_config(sub_scheme_code, module.PROMPT_CONFIG)
                    return module.PROMPT_CONFIG
            except (ImportError, AttributeError):
                pass
        
        return None
    
    def auto_discover_configs(self, base_path: str = "src/chatbot/schemas") -> None:
        """Auto-discover prompt configs from new schemas folder structure"""
        schemas_path = Path(base_path)
        if not schemas_path.exists():
            return
        
        for scheme_dir in schemas_path.iterdir():
            if not scheme_dir.is_dir() or not scheme_dir.name.startswith('s') or scheme_dir.name == '__pycache__':
                continue
            
            subs_dir = scheme_dir / "subs"
            if not subs_dir.exists():
                continue
            
            for subschema_dir in subs_dir.iterdir():
                if not subschema_dir.is_dir() or subschema_dir.name.startswith('_') or subschema_dir.name == '__pycache__':
                    continue
                
                config_file = subschema_dir / "prompt_config.py"
                if config_file.exists():
                    try:
                        module_path = f"src.chatbot.schemas.{scheme_dir.name}.subs.{subschema_dir.name}.prompt_config"
                        module = importlib.import_module(module_path)
                        if hasattr(module, 'PROMPT_CONFIG'):
                            self.register_config(subschema_dir.name, module.PROMPT_CONFIG)
                            logger.info(f"Auto-discovered prompt config: {subschema_dir.name}")
                    except Exception as e:
                        logger.warning(f"Failed to load prompt config {subschema_dir.name}: {e}")

# Global registry instance
subschema_prompt_registry = SubschemaPromptRegistry()

