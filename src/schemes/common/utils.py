"""Shared utilities for scheme implementations"""
from typing import List, Dict

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

