from typing import Tuple, Optional
from src.core.taluka.constants import DISTRICT_LEVEL
from src.core.taluka.orm_filter import TALUKA_SCOPE_ALL_OPTION

from ...shared.utils.validators import validate_numeric_inputs, MAX_INPUT_VALUE
from ...models import BudgetPostDetails
from ...derivation.mapping import pay_class_for


def validate_nps_value(value: Optional[str]) -> Tuple[bool, Optional[float], Optional[str]]:
    if value is None or value.strip() == "":
        return True, None, None

    try:
        float_value = float(value)
        if float_value < 0:
            return False, None, "नकारात्मक मूल्ये स्वीकार्य नाहीत"
        if float_value > MAX_INPUT_VALUE:
            return False, None, "मूल्य खूप मोठे आहे"
        return True, float_value, None
    except (ValueError, TypeError):
        return False, None, f"Invalid number format: '{value}'"


def validate_filled_against_sanctioned(db, record, filled_posts: int):
    """Validate a user-entered district total against consolidated Form D."""
    if record.class_type not in {'1', '2', '3', '4'}:
        return False, "अवैध पद वर्ग"

    rows = (
        db.query(BudgetPostDetails)
        .execution_options(**{TALUKA_SCOPE_ALL_OPTION: True})
        .filter(
            BudgetPostDetails.taluka == DISTRICT_LEVEL,
            BudgetPostDetails.district == record.district,
            BudgetPostDetails.fiscal_year == record.fiscal_year,
            BudgetPostDetails.category == record.category,
        )
        .all()
    )
    sanctioned = 0
    for row in rows:
        try:
            matches_class = (
                pay_class_for(row.class_type, row.designation) == record.class_type
            )
        except ValueError:
            continue
        if matches_class:
            sanctioned += int(row.sanctioned_posts_curr or 0)
    if filled_posts > sanctioned:
        return (
            False,
            f"भरलेली पदे ({filled_posts}) मंजूर पदांपेक्षा ({sanctioned}) जास्त असू शकत नाहीत",
        )
    return True, None

