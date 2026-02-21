"""Configuration for sub-scheme 22353408 - Welfare of the Elderly (Subsidies Non-Salary)."""
from src.core.base_config import BaseSchemeConfig, FormConfig


KONKAN_DISTRICTS = [
    "Mumbai City",
    "Mumbai Suburban",
    "Thane",
    "Palghar",
    "Raigad",
    "Ratnagiri",
    "Sindhudurg",
]


SCHEME_CONFIG = BaseSchemeConfig(
    code="22353408",
    parent_scheme="2235",
    scheme_type="voted",
    name_en="Welfare of the Elderly - Subsidies (Non-Salary)",
    name_mr="वृद्धांचे कल्याण - अनुदान (गैर-वेतन)",
    implemented=True,
    entry_point="/ui/s22353408/district-expenditure",
    completion_enabled=True,
    designations=[],
    designations_mr={},
    categories=[],
    categories_mr={},
    classes=[],
    classes_mr={},
    primary_units=[],
    primary_units_mr={},
    districts=KONKAN_DISTRICTS,
    forms={
        "district_expenditure": FormConfig(
            name="district_expenditure",
            table_name="district_expenditure_22353408",
            label_mr="जिल्हानिहाय खर्च",
            label_en="District-wise Expenditure",
            enabled=True,
        ),
    },
)
