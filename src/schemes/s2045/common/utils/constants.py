"""Shared constants for s2045 subschemes"""
from typing import Dict

CLASS_1_2_KEY = 'Class-1 & 2'
CLASS_3_KEY = 'Class-3'
CLASS_4_KEY = 'Class-4'
VALID_CLASS_KEYS = [CLASS_1_2_KEY, CLASS_3_KEY, CLASS_4_KEY]

CLASS_MAPPING: Dict[str, str] = {
    CLASS_1_2_KEY: 'वर्ग-1 व 2',
    CLASS_3_KEY: 'वर्ग-3',
    CLASS_4_KEY: 'वर्ग-4'
}

CLASS_MR_MAP: Dict[str, str] = {
    CLASS_1_2_KEY: 'वर्ग-1 व 2',
    CLASS_3_KEY: 'वर्ग-3',
    CLASS_4_KEY: 'वर्ग-4'
}

METRICS_DB_KEYS = [
    'posts', 'salary', 'grade_pay', 'special_pay', 'dearness_allowance',
    'local_supplementary_allowance', 'house_rent_allowance', 'travel_allowance', 'other'
]

METRICS_LABELS = [
    'पदे', 'वेतन', 'ग्रेड पे', 'एकूण वेतन', 'विशेष वेतन', 'महा.भत्ता',
    'स्था.पु.भ.', 'घरभाडे', 'प्रवास भत्ता', 'इतर', 'एकूण खर्च'
]
