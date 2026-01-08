"""Configuration for sub-scheme 20750249."""
from src.core.base_config import BaseSchemeConfig, FormConfig


SCHEME_CONFIG = BaseSchemeConfig(
    code="20750249",
    parent_scheme="2075",
    scheme_type="voted",
    name_en="Sub-Head Expenditure",
    name_mr="उपशिर्ष / गौणशिर्ष खर्च",
    implemented=True,
    entry_point="/ui/s20750249/sub-head-expenditure",
    completion_enabled=True,
    designations=[],
    designations_mr={},
    categories=[],
    categories_mr={},
    classes=[],
    classes_mr={},
    primary_units=[],
    primary_units_mr={},
    forms={
        "sub_head_expenditure": FormConfig(
            name="sub_head_expenditure",
            table_name="sub_head_expenditure_20750249",
            label_mr="उपशिर्ष / गौणशिर्ष खर्च",
            label_en="Sub-Head / Minor-Head Expenditure",
            enabled=True,
        )
    },
    districts=None,
)

