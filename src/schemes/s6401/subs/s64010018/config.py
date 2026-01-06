"""Configuration for sub-scheme 64010018 - Loans for Crop Husbandry."""
from src.core.base_config import BaseSchemeConfig


KONKAN_DISTRICTS = ["Thane", "Palghar", "Raigad", "Ratnagiri", "Sindhudurg"]


SCHEME_CONFIG = BaseSchemeConfig(
    code="64010018",
    parent_scheme="6401",
    scheme_type="voted",
    name_en="Loans for Crop Husbandry",
    name_mr="पीक उत्पादन कर्ज",
    implemented=True,
    entry_point="/ui/s64010018/district-expenditure",
    completion_enabled=True,
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


