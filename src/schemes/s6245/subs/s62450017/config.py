"""Configuration for sub-scheme 62450017 - Other Loans (Loans for Natural Calamities)."""
from src.core.base_config import BaseSchemeConfig


KONKAN_DISTRICTS = ["Thane", "Palghar", "Raigad", "Ratnagiri", "Sindhudurg"]


SCHEME_CONFIG = BaseSchemeConfig(
    code="62450017",
    parent_scheme="6245",
    scheme_type="voted",
    name_en="Other Loans for Natural Calamities",
    name_mr="इतर कर्जे (नैसर्गिक आपत्ती निवारणासाठी)",
    implemented=True,
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


