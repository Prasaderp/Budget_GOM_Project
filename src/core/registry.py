"""Central scheme registry for dynamic scheme loading and management"""
import importlib
import logging
from typing import Dict, Optional, List, Any, TYPE_CHECKING
from pathlib import Path

if TYPE_CHECKING:
    from fastapi import APIRouter
    from .base_config import BaseSchemeConfig

logger = logging.getLogger(__name__)

class SchemeRegistry:
    """Central registry for all scheme configurations and routers"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._schemes: Dict[str, 'BaseSchemeConfig'] = {}
        self._routers: Dict[str, 'APIRouter'] = {}
        self._main_schemes: Dict[str, Dict] = {}
        self._initialized = True
        
    def register_scheme(self, config: 'BaseSchemeConfig') -> None:
        """Register a scheme configuration"""
        self._schemes[config.code] = config
        
        # Track main scheme
        if config.parent_scheme not in self._main_schemes:
            self._main_schemes[config.parent_scheme] = {
                'sub_schemes': [],
                'charged': [],
                'voted': []
            }
        
        self._main_schemes[config.parent_scheme]['sub_schemes'].append(config.code)
        self._main_schemes[config.parent_scheme][config.scheme_type].append(config.code)
        
        logger.info(f"Registered scheme: {config.code} ({config.name_en})")
    
    def register_router(self, scheme_code: str, router: 'APIRouter') -> None:
        """Register a router for a scheme"""
        self._routers[scheme_code] = router
    
    def get_scheme(self, code: str) -> Optional['BaseSchemeConfig']:
        """Get scheme config by code"""
        return self._schemes.get(code)
    
    def get_router(self, code: str) -> Optional['APIRouter']:
        """Get router for scheme"""
        return self._routers.get(code)
    
    def get_all_schemes(self) -> Dict[str, 'BaseSchemeConfig']:
        """Get all registered schemes"""
        return self._schemes.copy()
    
    def get_implemented_schemes(self) -> Dict[str, 'BaseSchemeConfig']:
        """Get only implemented schemes"""
        return {k: v for k, v in self._schemes.items() if v.implemented}
    
    def get_main_schemes(self) -> Dict[str, Dict]:
        """Get main scheme groupings"""
        return self._main_schemes.copy()
    
    def get_schemes_by_type(self, scheme_type: str) -> Dict[str, 'BaseSchemeConfig']:
        """Get schemes filtered by type (charged/voted)"""
        return {k: v for k, v in self._schemes.items() if v.scheme_type == scheme_type}
    
    def get_schemes_by_parent(self, parent_code: str) -> Dict[str, 'BaseSchemeConfig']:
        """Get sub-schemes for a parent scheme"""
        return {k: v for k, v in self._schemes.items() if v.parent_scheme == parent_code}
    
    def is_implemented(self, code: str) -> bool:
        """Check if scheme is implemented"""
        scheme = self._schemes.get(code)
        return scheme.implemented if scheme else False
    
    def get_all_routers(self) -> List['APIRouter']:
        """Get all registered routers"""
        return list(self._routers.values())
    
    def get_template_path(self, scheme_code: str, template_name: str) -> str:
        """
        Get template path for a scheme with fallback logic.
        Resolution order:
        1. schemes/s{parent}/subs/s{code}/{template}
        2. schemes/s{parent}/base/{template}
        3. base/{template}
        """
        scheme = self._schemes.get(scheme_code)
        if not scheme:
            return f"base/{template_name}"
        
        parent = scheme.parent_scheme
        
        # Specific sub-scheme template
        specific = f"schemes/s{parent}/subs/s{scheme_code}/{template_name}"
        # Parent base template
        parent_base = f"schemes/s{parent}/base/{template_name}"
        # Global base template
        global_base = f"base/{template_name}"
        
        # Return in order - actual resolution happens at runtime
        return specific
    
    def auto_discover_schemes(self, base_path: str = "src/schemes") -> None:
        """
        Auto-discover and load schemes from folder structure.
        Looks for config.py in each sub-scheme folder.
        """
        schemes_path = Path(base_path)
        if not schemes_path.exists():
            logger.warning(f"Schemes path not found: {base_path}")
            return
        
        for main_scheme_dir in schemes_path.iterdir():
            if not main_scheme_dir.is_dir() or main_scheme_dir.name.startswith('_'):
                continue
            if main_scheme_dir.name in ('common', '__pycache__'):
                continue
                
            subs_dir = main_scheme_dir / "subs"
            if not subs_dir.exists():
                continue
                
            for sub_scheme_dir in subs_dir.iterdir():
                if not sub_scheme_dir.is_dir() or sub_scheme_dir.name.startswith('_'):
                    continue
                if sub_scheme_dir.name == '__pycache__':
                    continue
                    
                config_file = sub_scheme_dir / "config.py"
                if config_file.exists():
                    try:
                        module_path = f"src.schemes.{main_scheme_dir.name}.subs.{sub_scheme_dir.name}.config"
                        module = importlib.import_module(module_path)
                        if hasattr(module, 'SCHEME_CONFIG'):
                            self.register_scheme(module.SCHEME_CONFIG)
                            logger.info(f"Auto-discovered scheme: {sub_scheme_dir.name}")
                    except Exception as e:
                        logger.error(f"Failed to load scheme {sub_scheme_dir.name}: {e}")

# Global registry instance
scheme_registry = SchemeRegistry()

def get_registry() -> SchemeRegistry:
    """Get the global registry instance"""
    return scheme_registry

