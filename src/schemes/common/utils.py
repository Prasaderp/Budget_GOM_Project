"""Shared utilities for scheme implementations"""
from typing import List, Dict, Optional, Any

# Global Konkan Division districts (shared across schemes unless overridden)
GLOBAL_DISTRICTS = [
    'Mumbai City', 'Mumbai Suburban', 'Thane', 'Palghar',
    'Raigad', 'Ratnagiri', 'Sindhudurg'
]

GLOBAL_DISTRICTS_WITH_DCO = GLOBAL_DISTRICTS + ['DCO Staff']

GLOBAL_DISTRICTS_MR = {
    "Mumbai City": "मुंबई शहर",
    "Mumbai Suburban": "मुंबई उपनगर",
    "Thane": "ठाणे",
    "Palghar": "पालघर",
    "Raigad": "रायगड",
    "Ratnagiri": "रत्नागिरी",
    "Sindhudurg": "सिंधुदुर्ग",
    "DCO Staff": "जिल्हा संकलक कार्यालय कर्मचारी"
}

GLOBAL_CATEGORIES = ['Permanent', 'Temporary']
GLOBAL_CATEGORIES_MR = {"Permanent": "स्थायी", "Temporary": "अस्थायी"}

GLOBAL_STATUSES = ['Filled', 'Vacant']
GLOBAL_STATUSES_MR = {"Filled": "भरलेली", "Vacant": "रिक्त"}

def get_global_districts(include_dco: bool = True) -> List[str]:
    return GLOBAL_DISTRICTS_WITH_DCO if include_dco else GLOBAL_DISTRICTS

def get_global_categories() -> List[str]:
    return GLOBAL_CATEGORIES.copy()

def get_global_statuses() -> List[str]:
    return GLOBAL_STATUSES.copy()

def translate_to_marathi(value: str, mapping: Dict[str, str]) -> str:
    return mapping.get(value, value)


def get_post_expenses_nps_field_name(active_component: Optional[str]) -> str:
    if active_component == "SeventhPayCommissionDifferenceNPS":
        return "seventh_pay_commission_difference_nps"
    if active_component == "SeventhPayCommissionDifference":
        return "seventh_pay_commission_difference"
    return "nps"


def build_post_expenses_district_sync_update(
    *,
    active_component: Optional[str],
    medical_expenses: Optional[int],
    festival_advance: Optional[int],
    swagram_maharashtra_darshan: Optional[int],
    other: Optional[int],
    nps_unified: Optional[float],
) -> Dict[str, Any]:
    update_dict: Dict[str, Any] = {}
    if medical_expenses is not None:
        update_dict["medical_expenses"] = medical_expenses
    if festival_advance is not None:
        update_dict["festival_advance"] = festival_advance
    if swagram_maharashtra_darshan is not None:
        update_dict["swagram_maharashtra_darshan"] = swagram_maharashtra_darshan
    if other is not None:
        update_dict["other"] = other
    if nps_unified is not None:
        nps_field = get_post_expenses_nps_field_name(active_component)
        update_dict["nps"] = None
        update_dict["seventh_pay_commission_difference"] = None
        update_dict["seventh_pay_commission_difference_nps"] = None
        update_dict[nps_field] = nps_unified
    return update_dict


