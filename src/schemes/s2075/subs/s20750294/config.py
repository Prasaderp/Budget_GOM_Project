"""Configuration for sub-scheme 20750294."""
from src.core.base_config import BaseSchemeConfig


SCHEME_CONFIG = BaseSchemeConfig(
    code="20750294",
    parent_scheme="2075",
    scheme_type="voted",
    name_en="Sub-Head Expenditure",
    name_mr="उपशिर्ष / गौणशिर्ष खर्च",
    implemented=True,
    entry_point="/ui/s20750294/sub-head-expenditure",
    designations=[],
    designations_mr={},
    categories=[],
    categories_mr={},
    classes=[],
    classes_mr={},
    primary_units=[],
    primary_units_mr={},
    forms={},
    districts=None,
)

