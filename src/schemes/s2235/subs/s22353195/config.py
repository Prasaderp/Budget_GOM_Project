"""Configuration for sub-scheme 22353195 - Social Security and Welfare (District Expenditure)."""
from src.core.base_config import BaseSchemeConfig


KONKAN_DISTRICTS = [
    "Thane",
    "Palghar",
    "Raigad",
    "Ratnagiri",
    "Sindhudurg",
]


SCHEME_CONFIG = BaseSchemeConfig(
    code="22353195",
    parent_scheme="2235",
    scheme_type="voted",
    name_en="Social Security and Welfare - District Expenditure",
    name_mr="सामाजिक सुरक्षा व कल्याण - जिल्हानिहाय खर्च",
    implemented=True,
    entry_point="/ui/s22353195/district-expenditure",
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
