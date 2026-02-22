"""Configuration for scheme 2075 - Miscellaneous General Services.

Centralized configuration following the project's standard BaseSchemeConfig pattern.
"""
from src.core.base_config import BaseSchemeConfig, FormConfig

SCHEME_CODE = "2075"
SUB_SCHEME_CODE_249 = "20750249"
SUB_SCHEME_CODE_294 = "20750294"

DISTRICTS = ["Thane", "Palghar", "Raigad", "Sindhudurg"]

DISTRICTS_MR = {
    "Thane": "ठाणे",
    "Palghar": "पालघर",
    "Raigad": "रायगड",
    "Sindhudurg": "सिंधुदुर्ग",
}

SUB_HEAD_TEXT_249 = (
    "मागणी क्र.सी-4-2075- संकिर्ण-सर्वसाधारण सेवा 101- "
    "परत घेतलेल्या जहागिरी जमिनीऐवजी, निवृत्ती वेतन 101 (01) "
    "इनामदार व इतर अनुदानग्राही 04-निवृत्ती वेतने-(00) (01) "
    "आयुक्त कोकण (20750249)"
)

SUB_HEAD_TEXT_294 = (
    "मागणी क्र. सी-4-2075- संकिर्ण-सर्वसाधारण सेवा 101- "
    "परत घेतलेल्या जहागिरी जमिनीऐवजी निवृत्ती वेतन101 (02) "
    "परत घेतलेल्या जमीनी ऐवजी निवृत्ती वेतने 04-निवृत्ती वेतने (02) (01) "
    "आयुक्त कोकण (2075 0294)"
)

SHEET_NAMES = {
    "master": "2075 2019-20",
    "sub_head_249": "249",
    "district_294": "2075 294",
}

SCHEME_CONFIG = BaseSchemeConfig(
    code=SCHEME_CODE,
    parent_scheme=SCHEME_CODE,
    scheme_type="voted",
    name_en="Miscellaneous General Services - Pension",
    name_mr="विविध सामान्य सेवा - निवृत्ती वेतन",
    implemented=True,
    entry_point="/ui/s2075/expenditure",
    completion_enabled=True,
    designations=[],
    designations_mr={},
    categories=[],
    categories_mr={},
    classes=[],
    classes_mr={},
    primary_units=[],
    primary_units_mr={},
    forms={
        "sub_head_expenditure": FormConfig(
            name="sub_head_expenditure",
            table_name="sub_head_expenditure_2075",
            label_mr="निवृत्ती वेतन खर्च",
            label_en="Pension Expenditure",
            enabled=True,
        ),
        "district_expenditure": FormConfig(
            name="district_expenditure",
            table_name="district_expenditure_2075",
            label_mr="जिल्हानिहाय निवृत्ती वेतन खर्च",
            label_en="District-wise Pension Expenditure",
            enabled=True,
        ),
    },
    districts=DISTRICTS,
)
