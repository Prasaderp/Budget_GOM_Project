"""Configuration for sub-scheme 20450262 - Collection Recovery & Employment Cess."""
from src.core.base_config import BaseSchemeConfig, FormConfig

SCHEME_CODE = "2045"
SUB_SCHEME_CODE = "20450262"
TABLE_NAME = "district_expenditure_20450262"

# All 7 Konkan districts (includes Mumbai City & Mumbai Suburban)
KONKAN_DISTRICTS_FULL = [
    "Mumbai City",
    "Mumbai Suburban",
    "Thane",
    "Palghar",
    "Raigad",
    "Ratnagiri",
    "Sindhudurg",
]

SCHEME_CONFIG = BaseSchemeConfig(
    code=SUB_SCHEME_CODE,
    parent_scheme=SCHEME_CODE,
    scheme_type="voted",
    name_en="Collection Recovery & Employment Cess Expenditure",
    name_mr="वसुलीचा इतर खर्च - रोजगार हमी उपकर (2045 0262)",
    implemented=True,
    entry_point=f"/ui/s{SUB_SCHEME_CODE}/district-expenditure",
    completion_enabled=True,
    designations=[],
    designations_mr={},
    categories=[],
    categories_mr={},
    classes=[],
    classes_mr={},
    primary_units=[],
    primary_units_mr={},
    districts=KONKAN_DISTRICTS_FULL,
    forms={
        "district_expenditure": FormConfig(
            name="district_expenditure",
            table_name=TABLE_NAME,
            label_en="District Expenditure",
            label_mr="जिल्हा खर्च"
        )
    },
)
