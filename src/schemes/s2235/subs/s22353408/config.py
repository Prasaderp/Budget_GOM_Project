"""Configuration for sub-scheme 22353408 - Welfare of the Elderly (Subsidies Non-Salary)."""
from src.core.base_config import BaseSchemeConfig


KONKAN_DISTRICTS = ["Mumbai City", "Mumbai Suburban", "Thane", "Palghar", "Raigad", "Ratnagiri", "Sindhudurg"]


SCHEME_CONFIG = BaseSchemeConfig(
    code="22353408",
    parent_scheme="2235",
    scheme_type="voted",
    name_en="Welfare of the Elderly - Subsidies (Non-Salary)",
    name_mr="वृद्धांचे कल्याण - अनुदान (गैर-वेतन)",
    implemented=True,
    entry_point="/ui/s22353408/district-expenditure",
    designations=[],
    designations_mr={},
    categories=[],
    categories_mr={},
    classes=[],
    classes_mr={},
    primary_units=[],
    primary_units_mr={},
    forms={},
)

