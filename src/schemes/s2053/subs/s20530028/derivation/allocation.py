"""Form C's Filled/Vacant allocation - the user-owned split inside a derived total.

Form D fixes each class total exactly (LINK 1, 48/48 cells). It says nothing
about how that total divides between Filled and Vacant: plan section 2.8 C2
measured every candidate rule and found none that reproduces the workbook. The
split is therefore user data. It is authored on the Filled row, and this module
maintains the one invariant that lets an editable Filled coexist with a derived
total (plan section 4.1 STEP E):

    Filled[m] + Vacant[m] == Form D class total[m]

Never commits, never rolls back - the caller owns the transaction, the same
contract consolidate_row() gives.
"""

import logging

from fastapi import HTTPException

from src.core.taluka.constants import DISTRICT_LEVEL, TOTAL_SPACE_FLAG
from src.core.taluka.models import natural_key_columns
from src.core.taluka.orm_filter import TALUKA_SCOPE_ALL_OPTION
from src.core.taluka.write import ensure_contribution_row
from src.core.taluka.consolidation import consolidate_row
from src.utils_da_rate import get_da_rate

from ..config import (
    ALLOCATABLE_POST_STATUS_FIELDS,
    VALID_CLASS_KEYS,
)
from ..models import PostStatus
from ..shared.services.audit_service import AuditService
from .aggregator import CellTotals, aggregate_pay_classes, roll_up_to_status_classes

logger = logging.getLogger(__name__)

FILLED_STATUS = "Filled"
VACANT_STATUS = "Vacant"


def scan_space_for(row) -> str:
    """The taluka space whose Form D rows bound `row`'s values.

    A lifted row holds district totals (write.py:_lift_to_total_space), so its
    ceiling is the consolidated Form D scan; any other row holds its own
    contribution and is bounded by that same contribution's Form D rows.
    """
    if getattr(row, TOTAL_SPACE_FLAG, False):
        return DISTRICT_LEVEL
    return row.taluka


def class_totals_for(db, row, *, taluka: str) -> CellTotals:
    """Form D's derived total for `row`'s class, in one exact space."""
    if row.class_type not in VALID_CLASS_KEYS:
        raise ValueError(f"Unsupported Form C class_type: {row.class_type!r}")
    pay_totals = aggregate_pay_classes(
        db,
        taluka=taluka,
        district=row.district,
        fiscal_year=row.fiscal_year,
        category=row.category,
        da_rate=get_da_rate(db, row.fiscal_year),
    )
    return roll_up_to_status_classes(pay_totals)[row.class_type]


def _vacant_sibling(db, filled_row):
    key_cols = [c for c in natural_key_columns(PostStatus) if c != "status"]
    consolidated = (
        db.query(PostStatus)
        .execution_options(**{TALUKA_SCOPE_ALL_OPTION: True})
        .filter(
            PostStatus.taluka == DISTRICT_LEVEL,
            PostStatus.status == VACANT_STATUS,
            *[getattr(PostStatus, c) == getattr(filled_row, c) for c in key_cols],
        )
        .first()
    )
    if consolidated is None:
        logger.error(
            "form_allocation_missing_consolidated table=%s district=%s fiscal_year=%s "
            "category=%s class=%s status=%s",
            PostStatus.__tablename__,
            filled_row.district,
            filled_row.fiscal_year,
            filled_row.category,
            filled_row.class_type,
            VACANT_STATUS,
        )
        raise RuntimeError(
            f"Missing consolidated {PostStatus.__tablename__} Vacant row for "
            f"{filled_row.district}/{filled_row.fiscal_year}/{filled_row.category}/"
            f"{filled_row.class_type}"
        )
    return ensure_contribution_row(db, PostStatus, consolidated, filled_row.taluka)


def rebalance_status_split(db, filled_row, request=None) -> int:
    """Force Vacant[m] = total[m] - Filled[m] for the eight money measures.

    Runs after consolidate_row() has rebased the edited row out of total space,
    so both rows and the Form D scan share one contribution space. `posts` is
    never touched here - it is owned by derive_from_form_d via LINK 3.
    """
    if getattr(filled_row, TOTAL_SPACE_FLAG, False):
        raise RuntimeError(
            "Cannot rebalance a lifted total-space row "
            f"{filled_row.__tablename__}/{filled_row.id}"
        )
    if filled_row.status != FILLED_STATUS:
        raise HTTPException(
            status_code=409,
            detail="प्रपत्र क मधील रिक्त मूल्ये भरलेली पदांवरून स्वयंचलितपणे गणली जातात",
        )
    if not filled_row.taluka or filled_row.taluka == DISTRICT_LEVEL:
        raise RuntimeError(
            "Rebalance must target a contribution taluka, never taluka=''"
        )

    totals = class_totals_for(db, filled_row, taluka=filled_row.taluka)
    vacant_row = _vacant_sibling(db, filled_row)

    old_values = {f: getattr(vacant_row, f) for f in ALLOCATABLE_POST_STATUS_FIELDS}
    changed = 0
    for measure in ALLOCATABLE_POST_STATUS_FIELDS:
        total = getattr(totals, measure)
        filled = int(getattr(filled_row, measure) or 0)
        if filled > total:
            logger.warning(
                "form_allocation_clamp district=%s taluka=%s fiscal_year=%s category=%s "
                "class=%s measure=%s filled=%s total=%s",
                filled_row.district,
                filled_row.taluka,
                filled_row.fiscal_year,
                filled_row.category,
                filled_row.class_type,
                measure,
                filled,
                total,
            )
        vacant = max(0, total - filled)
        if getattr(vacant_row, measure) != vacant:
            logger.info(
                "form_allocation_changed district=%s taluka=%s fiscal_year=%s category=%s "
                "class=%s status=Vacant field=%s old=%s new=%s",
                filled_row.district,
                filled_row.taluka,
                filled_row.fiscal_year,
                filled_row.category,
                filled_row.class_type,
                measure,
                getattr(vacant_row, measure),
                vacant,
            )
            setattr(vacant_row, measure, vacant)
            changed += 1

    if changed and request is not None:
        AuditService.log_action(
            db=db,
            request=request,
            action="DERIVE",
            table_name=vacant_row.__tablename__,
            record_id=vacant_row.id,
            old_values=old_values,
            new_values={
                f: getattr(vacant_row, f) for f in ALLOCATABLE_POST_STATUS_FIELDS
            },
        )

    db.flush()
    consolidate_row(
        db,
        PostStatus,
        vacant_row.district,
        vacant_row.fiscal_year,
        {c: getattr(vacant_row, c) for c in natural_key_columns(PostStatus)},
    )
    return changed
