"""Global configuration for Budget Management System

This file contains GLOBAL configs shared across all schemes.
Scheme-specific configs are in: src/schemes/s{code}/subs/s{subcode}/config.py
"""
from typing import List, Dict
import os

# ==============================================================================
# GLOBAL CONFIGURATIONS (shared across all schemes)
# ==============================================================================

DCO_STAFF_IDENTIFIER = 'DCO Staff'

# Konkan Division districts (7 districts + DCO Staff)
REGULAR_DISTRICTS: List[str] = [
    'Mumbai City', 'Mumbai Suburban', 'Thane', 'Palghar',
    'Raigad', 'Ratnagiri', 'Sindhudurg'
]

DISTRICTS: List[str] = REGULAR_DISTRICTS + [DCO_STAFF_IDENTIFIER]

DISTRICTS_MR = {
    "Mumbai City": "मुंबई शहर",
    "Mumbai Suburban": "मुंबई उपनगर", 
    "Thane": "ठाणे",
    "Palghar": "पालघर",
    "Raigad": "रायगड",
    "Ratnagiri": "रत्नागिरी",
    "Sindhudurg": "सिंधुदुर्ग",
    "DCO Staff": "जिल्हा संकलक कार्यालय कर्मचारी",
    "Divisional Commissioner": "विभागीय आयुक्त"
}

# ==============================================================================
# ROW LIMITS (defaults, can be overridden per-scheme)
# ==============================================================================

BUDGET_POST_DETAILS_ROW_LIMIT = 217
POST_STATUS_ROW_LIMIT = 87
POST_EXPENSES_ROW_LIMIT = 56
UNIT_EXPENDITURE_ROW_LIMIT = 104

# ==============================================================================
# BACKWARD COMPATIBILITY IMPORTS
# These imports are kept for backward compatibility with existing code.
# New code should import directly from scheme-specific config files.
# ==============================================================================

from src.schemes.s2053.subs.s20530028.config import (
    CATEGORIES, CATEGORIES_MR,
    STATUSES, STATUSES_MR,
    CLASSES_SHEET1_2, CLASSES_MR,
    CLASSES_SHEET3, CLASSES_SHEET3_MR,
    DESIGNATIONS, DESIGNATIONS_MR,
    PRIMARY_UNITS, PRIMARY_UNITS_MR, UNIT_ACCOUNT_MAP_MR,
    POSITION_ORDER, POST_EXPENSES_DISTRICT_COMPONENT,
    MARATHI_TO_ENGLISH_DESIGNATIONS
)

POST_EXPENSES_DISTRICT_COMPONENT_FIELD = POST_EXPENSES_DISTRICT_COMPONENT

POSITION_SORT_MAP = {name: i for i, name in enumerate(POSITION_ORDER)}
