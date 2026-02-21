"""Configuration for sub-scheme 20450251 - Education Cess Grants to Village Panchayats."""
from src.core.base_config import BaseSchemeConfig, FormConfig

SCHEME_CODE = "2045"
SUB_SCHEME_CODE = "20450251"
TABLE_NAME = "district_expenditure_20450251"

# 5 Konkan districts only (NO Mumbai City & Mumbai Suburban)
KONKAN_DISTRICTS_NO_MUMBAI = [
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
    name_en="Education Cess Grants to Village Panchayats",
    name_mr="महा. शिक्षण उपकर अधि कलम 23 अन्वये ग्रामपंचायतीना प्रदाने (2045 0251)",
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
    districts=KONKAN_DISTRICTS_NO_MUMBAI,
    forms={
        "district_expenditure": FormConfig(
            name="district_expenditure",
            table_name=TABLE_NAME,
            label_en="District Expenditure",
            label_mr="जिल्हा खर्च"
        )
    },
)
