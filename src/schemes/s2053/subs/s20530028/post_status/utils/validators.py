"""Validators for Post Status module"""

from typing import Mapping, Tuple, Optional
from ...config import (
    ALLOCATABLE_POST_STATUS_FIELDS,
    POST_STATUS_FIELD_LABELS_MR,
    VALID_CLASS_KEYS,
)
from ...derivation.allocation import FILLED_STATUS, class_totals_for, scan_space_for
from ...shared.utils.validators import MAX_INPUT_VALUE


def validate_post_status_inputs(
    posts: Optional[int] = None,
    salary: Optional[int] = None,
    grade_pay: Optional[int] = None,
    special_pay: Optional[int] = None,
    dearness_allowance: Optional[int] = None,
    local_supplementary_allowance: Optional[int] = None,
    house_rent_allowance: Optional[int] = None,
    travel_allowance: Optional[int] = None,
    other: Optional[int] = None,
    max_value: int = MAX_INPUT_VALUE,
) -> Tuple[bool, Optional[str]]:
    """
    Validate numeric inputs are non-negative and within max value

    Returns:
        tuple: (is_valid, error_message)
    """
    values = [
        posts,
        salary,
        grade_pay,
        special_pay,
        dearness_allowance,
        local_supplementary_allowance,
        house_rent_allowance,
        travel_allowance,
        other,
    ]

    if any(v is not None and v < 0 for v in values):
        return False, "नकारात्मक मूल्ये स्वीकार्य नाहीत"

    if any(v is not None and v > max_value for v in values):
        return False, "मूल्य खूप मोठे आहे"

    return True, None


def validate_allocation(
    db, record, values: Mapping[str, Optional[int]]
) -> Tuple[bool, Optional[str]]:
    """Bound a user-typed Filled allocation by Form D's class total.

    Runs on the row as resolve_editable_row() returned it, so a district or DCO
    caller is checked against the consolidated Form D scan it just typed
    district totals against, and a taluka caller against its own contribution.
    Same total-vs-share distinction as validate_filled_against_sanctioned.
    """
    if record.status != FILLED_STATUS:
        return False, "फक्त भरलेली पदांची मूल्ये संपादित करता येतात"
    if record.class_type not in VALID_CLASS_KEYS:
        return False, "अवैध पद वर्ग"

    totals = class_totals_for(db, record, taluka=scan_space_for(record))
    for field in ALLOCATABLE_POST_STATUS_FIELDS:
        value = values.get(field)
        if value is None:
            continue
        ceiling = getattr(totals, field)
        if value > ceiling:
            label = POST_STATUS_FIELD_LABELS_MR.get(field, field)
            return (
                False,
                f"{label} ({value}) प्रपत्र ड मधील एकूण ({ceiling}) पेक्षा जास्त असू शकत नाही",
            )
    return True, None
