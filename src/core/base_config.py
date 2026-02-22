"""Base configuration classes for scheme definitions"""
from typing import Dict, List, Optional, Any, Type
from dataclasses import dataclass, field
from enum import Enum

class FieldType(Enum):
    INTEGER = "integer"
    FLOAT = "float"
    STRING = "string"
    DECIMAL = "decimal"
    BOOLEAN = "boolean"

@dataclass
class FieldConfig:
    name: str
    db_column: str
    field_type: FieldType
    label_mr: str
    label_en: str
    required: bool = False
    default: Any = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    editable: bool = True
    
@dataclass
class FormConfig:
    name: str
    table_name: str
    label_mr: str
    label_en: str
    fields: List[FieldConfig] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    classes: List[str] = field(default_factory=list)
    statuses: List[str] = field(default_factory=list)
    enabled: bool = True

@dataclass
class BaseSchemeConfig:
    code: str
    parent_scheme: str
    scheme_type: str
    name_en: str
    name_mr: str
    implemented: bool = False
    entry_point: Optional[str] = None
    completion_enabled: bool = False
    
    forms: Dict[str, FormConfig] = field(default_factory=dict)
    
    districts: Optional[List[str]] = None
    districts_mr: Optional[Dict[str, str]] = None
    
    designations: List[str] = field(default_factory=list)
    designations_mr: Dict[str, str] = field(default_factory=dict)
    
    categories: List[str] = field(default_factory=list)
    categories_mr: Dict[str, str] = field(default_factory=dict)
    
    classes: List[str] = field(default_factory=list)
    classes_mr: Dict[str, str] = field(default_factory=dict)
    
    primary_units: List[str] = field(default_factory=list)
    primary_units_mr: Dict[str, str] = field(default_factory=dict)
    
    def get_form(self, form_name: str) -> Optional[FormConfig]:
        return self.forms.get(form_name)
    
    def is_form_enabled(self, form_name: str) -> bool:
        form = self.forms.get(form_name)
        return form.enabled if form else False
    
    def get_entry_point(self) -> str:
        """Get entry point URL, with fallback to default"""
        if self.entry_point:
            return self.entry_point
        return "/ui/budget-post-details?view=edit"

def create_scheme_config(
    code: str,
    parent_scheme: str,
    scheme_type: str,
    name_en: str,
    name_mr: str,
    **kwargs
) -> BaseSchemeConfig:
    """Factory function to create scheme config"""
    return BaseSchemeConfig(
        code=code,
        parent_scheme=parent_scheme,
        scheme_type=scheme_type,
        name_en=name_en,
        name_mr=name_mr,
        **kwargs
    )

