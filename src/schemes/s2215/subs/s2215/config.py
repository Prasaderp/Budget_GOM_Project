"""Configuration for sub-scheme 2215 - Water Scarcity."""
from src.core.base_config import BaseSchemeConfig
from src.schemes.common.utils import GLOBAL_DISTRICTS

# Konkan division districts (as per the table structure)
KONKAN_DISTRICTS = ["Thane", "Palghar", "Raigad", "Ratnagiri", "Sindhudurg"]

# Account heads configuration
# Each account head represents a major budget category under scheme 2215
ACCOUNT_HEADS = [
    {
        "code": "2215A195",
        "text_mr": "मागणी क्र. वाय-2, मुख्यलेखाशीर्ष 2215 पाणी पुरवठा व स्वच्छता, 01, पाणी पुरवठा, 196 जिल्हा परिषद पंचायत / संस्थाना सहाय्य, 02 जिल्हा परिषदांना अनुदान, (02) (03) आकस्मिक पिण्याच्या पाण्याच्या टंचाई निवारणार्थ घेण्यात येणा-या तात्पुरत्या उपाय योजनांसाठी जिल्हा परिषदांना सहाय्यक अनुदान (अनिवार्य), 31, सहाय्यक अनुदाने (वेतनेत्तर) (2215 ए 195)",
        "text_en": "Demand No. Y-2, Major Head 2215 Water Supply and Sanitation, 01, Water Supply, 196 Zilla Parishad Panchayat/Institution Assistance, 02 Grants to Zilla Parishads, (02) (03) Temporary measures for emergency drinking water scarcity relief - Grant-in-aid to Zilla Parishads (Mandatory), 31, Grant-in-aid (Non-salary) (2215 A 195)",
        "district_offices": [
            "Chief Executive Officer, Zilla Parishad Thane",
            "Chief Executive Officer, Zilla Parishad Palghar",
            "Chief Executive Officer, Zilla Parishad Raigad",
            "Chief Executive Officer, Zilla Parishad Ratnagiri",
            "Chief Executive Officer, Zilla Parishad Sindhudurg",
        ],
    },
    {
        "code": "2215A201",
        "text_mr": "2215A201 (शहरी भागासाठी) पाणी टंचाई",
        "text_en": "2215A201 (For Urban Area) Water Scarcity",
        "district_offices": [
            "Collector Thane",
            "Collector Palghar",
            "Collector Raigad",
            "Collector Ratnagiri",
            "Collector Sindhudurg",
        ],
    },
]

# Division total identifier
DIVISION_TOTAL_DISTRICT = "Total-Konkan Division"
DIVISION_TOTAL_DISTRICT_MR = "एकूण-कोकण विभाग"

# District office Marathi translations
DISTRICT_OFFICES_MR = {
    "Chief Executive Officer, Zilla Parishad Thane": "मुख्य कार्यकारी अधिकारी, जिल्हा परिषद ठाणे",
    "Chief Executive Officer, Zilla Parishad Palghar": "मुख्य कार्यकारी अधिकारी, जिल्हा परिषद पालघर",
    "Chief Executive Officer, Zilla Parishad Raigad": "मुख्य कार्यकारी अधिकारी, जिल्हा परिषद रायगड",
    "Chief Executive Officer, Zilla Parishad Ratnagiri": "मुख्य कार्यकारी अधिकारी, जिल्हा परिषद रत्नागिरी",
    "Chief Executive Officer, Zilla Parishad Sindhudurg": "मुख्य कार्यकारी अधिकारी, जिल्हा परिषद सिंधुदुर्ग",
    "Collector Thane": "जिल्हाधिकारी ठाणे",
    "Collector Palghar": "जिल्हाधिकारी पालघर",
    "Collector Raigad": "जिल्हाधिकारी रायगड",
    "Collector Ratnagiri": "जिल्हाधिकारी रत्नागिरी",
    "Collector Sindhudurg": "जिल्हाधिकारी सिंधुदुर्ग",
}

# Notification messages in Marathi
NOTIFICATIONS_MR = {
    "update_success": "रेकॉर्ड यशस्वीरित्या अपडेट झाला",
    "update_failed": "रेकॉर्ड अपडेट करण्यात अयशस्वी",
    "record_not_found": "निवडलेल्या मापदंडांसाठी रेकॉर्ड सापडला नाही",
    "update_error": "अपडेट करताना त्रुटी",
}


def get_account_head(code: str) -> dict:
    """Get account head configuration by code."""
    for head in ACCOUNT_HEADS:
        if head["code"] == code:
            return head
    return None


def get_all_account_heads() -> list:
    """Get all account head configurations."""
    return ACCOUNT_HEADS.copy()


def get_districts_for_account_head(account_head_code: str) -> list:
    """Get district offices for a specific account head."""
    head = get_account_head(account_head_code)
    if not head:
        return KONKAN_DISTRICTS
    return head.get("district_offices", KONKAN_DISTRICTS)


SCHEME_CONFIG = BaseSchemeConfig(
    code="2215",
    parent_scheme="2215",
    scheme_type="voted",
    name_en="Water Scarcity",
    name_mr="पाणी टंचाई",
    implemented=True,
    entry_point="/ui/s2215",
    designations=[],
    designations_mr={},
    categories=[],
    categories_mr={},
    classes=[],
    classes_mr={},
    primary_units=[],
    primary_units_mr={},
    districts=KONKAN_DISTRICTS,
    forms={},
)

