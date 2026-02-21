"""Configuration for sub-scheme 76101871."""
from src.core.base_config import BaseSchemeConfig, FormConfig
from src.schemes.common.utils import GLOBAL_DISTRICTS_WITH_DCO


KONKAN_DISTRICTS = GLOBAL_DISTRICTS_WITH_DCO


SCHEME_CONFIG = BaseSchemeConfig(
    code="76101871",
    parent_scheme="7610",
    scheme_type="voted",
    name_en="District Expenditure",
    name_mr="जिल्हानिहाय खर्च",
    implemented=True,
    entry_point="/ui/s76101871/district-expenditure",
    completion_enabled=True,
    districts=KONKAN_DISTRICTS,
    designations=[],
    designations_mr={},
    categories=[],
    categories_mr={},
    classes=[],
    classes_mr={},
    primary_units=[],
    primary_units_mr={},
    forms={
        "district_expenditure": FormConfig(
            name="district_expenditure",
            table_name="district_expenditure_76101871",
            label_mr="जिल्हानिहाय खर्च",
            label_en="District Expenditure",
            enabled=True,
        )
    },
)



