"""Pure mappings from Form D rows to the connected Form C/Form B vocabulary.

Form D owns the dearness-allowance and house-rent arithmetic. If those client-owned
expressions change, the two adapters in this module are the only propagation code
that must follow them.
"""

import logging
from operator import attrgetter

from ..config import (
    CLASS_1_2_KEY,
    CLASS_3_KEY,
    CLASS_4_KEY,
    DESIGNATION_PAY_CLASS,
    HRA_RATE_MAP,
    PAY_CLASS_TO_STATUS_CLASS,
)

logger = logging.getLogger(__name__)


def pay_class_for(class_type: str, designation: str) -> str:
    """Return Form B's pay class for one Form D row."""
    if class_type == CLASS_3_KEY:
        return '3'
    if class_type == CLASS_4_KEY:
        return '4'
    if class_type != CLASS_1_2_KEY:
        raise ValueError(f"Unsupported Form D class_type: {class_type!r}")

    pay_class = DESIGNATION_PAY_CLASS.get(designation)
    if pay_class is None:
        logger.warning(
            "Unknown Class-1 & 2 designation %r; defaulting to pay class 2",
            designation,
        )
        return '2'
    return pay_class


def status_class_for(pay_class: str) -> str:
    """Collapse Form B's four pay classes into Form C's three class groups."""
    try:
        return PAY_CLASS_TO_STATUS_CLASS[pay_class]
    except KeyError as exc:
        raise ValueError(f"Unsupported Form B pay class: {pay_class!r}") from exc


def form_d_dearness_allowance(row, da_rate: float) -> int:
    """Reproduce the value rendered by Form D for one row."""
    return round((float(row.basic_pay) + float(row.grade_pay)) * da_rate)


def form_d_house_rent_allowance(row) -> int:
    """Reproduce the value rendered by Form D for one row."""
    return round(
        (float(row.basic_pay) + float(row.grade_pay))
        * HRA_RATE_MAP[row.hra_rate]
    )


def _other_allowances(row):
    return (
        row.washing_allowance
        + row.cash_allowance
        + row.footwear_allowance_other
    )


MEASURE_MAP = (
    ('salary', attrgetter('basic_pay')),
    ('grade_pay', attrgetter('grade_pay')),
    ('special_pay', attrgetter('special_pay')),
    ('dearness_allowance', form_d_dearness_allowance),
    ('local_supplementary_allowance', attrgetter('local_supplementary_allowance')),
    ('house_rent_allowance', form_d_house_rent_allowance),
    ('travel_allowance', attrgetter('vehicle_allowance')),
    ('other', _other_allowances),
)
