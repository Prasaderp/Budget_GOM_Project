"""Configuration for sub-scheme 22350338 - Social Security and Welfare (District Expenditure)."""
from src.core.base_config import BaseSchemeConfig, FormConfig


KONKAN_DISTRICTS = [
    "Divisional Commissioner",
    "Mumbai City",
    "Mumbai Suburban",
    "Thane",
    "Palghar",
    "Raigad",
    "Ratnagiri",
    "Sindhudurg",
]


SCHEME_CONFIG = BaseSchemeConfig(
    code="22350338",
    parent_scheme="2235",
    scheme_type="voted",
    name_en="Social Security and Welfare - District Expenditure",
    name_mr="सामाजिक सुरक्षा व कल्याण - जिल्हानिहाय खर्च",
    implemented=True,
    entry_point="/ui/s22350338/district-expenditure",
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
            table_name="district_expenditure_22350338",
            label_mr="जिल्हानिहाय खर्च",
            label_en="District-wise Expenditure",
            enabled=True,
        ),
    },
)
