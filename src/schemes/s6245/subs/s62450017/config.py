"""Configuration for sub-scheme 62450017 - Other Loans (Loans for Natural Calamities)."""
from src.core.base_config import BaseSchemeConfig, FormConfig


KONKAN_DISTRICTS = ["Thane", "Palghar", "Raigad", "Ratnagiri", "Sindhudurg"]


SCHEME_CONFIG = BaseSchemeConfig(
    code="62450017",
    parent_scheme="6245",
    scheme_type="voted",
    name_en="Other Loans for Natural Calamities",
    name_mr="इतर कर्जे (नैसर्गिक आपत्ती निवारणासाठी)",
    implemented=True,
    entry_point="/ui/s62450017/district-expenditure",
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
            table_name="district_expenditure_62450017",
            label_mr="जिल्हानिहाय खर्च",
            label_en="District-wise Expenditure",
            enabled=True,
        ),
    },
)


