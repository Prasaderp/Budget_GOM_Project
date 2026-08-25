"""Transactional writer for Form D -> Form B/Form C derivation.

The caller owns commit and rollback. Lock order is always:
BudgetPostDetails consolidated row (already held by Form D controllers),
PostExpenses classes 1..4, then PostStatus classes/statuses in configured order.
"""

from dataclasses import dataclass
import logging
from time import perf_counter

from sqlalchemy import case

from src.core.taluka.consolidation import consolidate_row
from src.core.taluka.constants import DISTRICT_LEVEL, DISTRICT_OFFICE, TOTAL_SPACE_FLAG
from src.core.taluka.models import natural_key_columns
from src.core.taluka.orm_filter import TALUKA_SCOPE_ALL_OPTION
from src.core.taluka.write import _writable_taluka_value, ensure_contribution_row
from src.utils_auth import get_auth_level, get_auth_unit
from src.utils_da_rate import get_da_rate

from ..config import (
    DERIVED_POST_EXPENSES_FIELDS,
    DERIVED_POST_STATUS_FIELDS,
    PAY_CLASS_TO_STATUS_CLASS,
    STATUSES,
    VALID_CLASS_KEYS,
)
from ..models import BudgetPostDetails, PostExpenses, PostStatus
from ..shared.services.audit_service import AuditService
from .aggregator import PAY_CLASSES, aggregate_pay_classes, roll_up_to_status_classes
from .split_policy import SPLIT_POLICY

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DerivationResult:
    rows_written: int
    fields_changed: int
    clamps: int


@dataclass(frozen=True)
class _LockedRows:
    expenses: dict[str, PostExpenses]
    statuses: dict[tuple[str, str], PostStatus]


def _unscoped(query):
    return query.execution_options(**{TALUKA_SCOPE_ALL_OPTION: True})


def _require_complete_rows(table_name, rows, expected_keys, key_fn):
    indexed = {key_fn(row): row for row in rows}
    missing = [key for key in expected_keys if key not in indexed]
    if missing:
        logger.error(
            "form_derivation_missing_consolidated table=%s natural_keys=%s",
            table_name,
            missing,
        )
        raise RuntimeError(
            f"Missing consolidated {table_name} rows for natural keys: {missing}"
        )
    return indexed


def acquire_derivation_locks(
    db, district: str, fiscal_year: str, category: str
) -> _LockedRows:
    """Lock every affected consolidated Form B/Form C row deterministically."""
    if not district or not fiscal_year or not category:
        raise ValueError("district, fiscal_year and category are required")

    expense_rows = (
        _unscoped(db.query(PostExpenses))
        .filter(
            PostExpenses.taluka == DISTRICT_LEVEL,
            PostExpenses.district == district,
            PostExpenses.fiscal_year == fiscal_year,
            PostExpenses.category == category,
            PostExpenses.class_type.in_(PAY_CLASSES),
        )
        .order_by(PostExpenses.class_type)
        .with_for_update()
        .all()
    )
    expenses = _require_complete_rows(
        PostExpenses.__tablename__, expense_rows, PAY_CLASSES, lambda row: row.class_type
    )

    class_order = case(
        {value: index for index, value in enumerate(VALID_CLASS_KEYS)},
        value=PostStatus.class_type,
    )
    status_order = case(
        {value: index for index, value in enumerate(STATUSES)},
        value=PostStatus.status,
    )
    status_rows = (
        _unscoped(db.query(PostStatus))
        .filter(
            PostStatus.taluka == DISTRICT_LEVEL,
            PostStatus.district == district,
            PostStatus.fiscal_year == fiscal_year,
            PostStatus.category == category,
            PostStatus.class_type.in_(VALID_CLASS_KEYS),
            PostStatus.status.in_(STATUSES),
        )
        .order_by(class_order, status_order)
        .with_for_update()
        .all()
    )
    expected_statuses = tuple(
        (class_type, status)
        for class_type in VALID_CLASS_KEYS
        for status in STATUSES
    )
    statuses = _require_complete_rows(
        PostStatus.__tablename__,
        status_rows,
        expected_statuses,
        lambda row: (row.class_type, row.status),
    )
    return _LockedRows(expenses=expenses, statuses=statuses)


def _natural_key(row, model):
    return {name: getattr(row, name) for name in natural_key_columns(model)}


def _snapshot(row, fields):
    return {field: getattr(row, field) for field in fields}


def _record_changes(db, request, row, fields, values, *, context):
    old_values = _snapshot(row, fields)
    changed = 0
    for field, value in values.items():
        if field not in fields:
            raise AssertionError(f"Attempted non-derived write: {field}")
        if value < 0:
            raise AssertionError(f"Derived value cannot be negative: {field}={value}")
        old = getattr(row, field)
        if old != value:
            setattr(row, field, value)
            changed += 1
            logger.info(
                "form_derivation_changed %s field=%s old=%s new=%s",
                context,
                field,
                old,
                value,
            )
    if changed and request is not None:
        AuditService.log_action(
            db=db,
            request=request,
            action="DERIVE",
            table_name=row.__tablename__,
            record_id=row.id,
            old_values=old_values,
            new_values=_snapshot(row, fields),
        )
    return changed


def derive_from_form_d(
    db,
    *,
    district: str,
    fiscal_year: str,
    category: str,
    taluka: str,
    request=None,
) -> DerivationResult:
    """Recompute one contribution space without committing or rolling back."""
    if not taluka or taluka == DISTRICT_LEVEL:
        raise ValueError("Derivation must target a contribution taluka, never taluka='' ")

    started = perf_counter()
    locked = acquire_derivation_locks(db, district, fiscal_year, category)
    pay_totals = aggregate_pay_classes(
        db,
        taluka=taluka,
        district=district,
        fiscal_year=fiscal_year,
        category=category,
        da_rate=get_da_rate(db, fiscal_year),
    )

    changed_rows: set[tuple[str, int]] = set()
    fields_changed = 0
    clamps = 0
    expense_contributions = {}

    for pay_class in PAY_CLASSES:
        row = ensure_contribution_row(db, PostExpenses, locked.expenses[pay_class], taluka)
        expense_contributions[pay_class] = row
        sanctioned = pay_totals[pay_class].sanctioned
        filled = int(row.filled_posts or 0)
        vacant = max(0, sanctioned - filled)
        if filled > sanctioned:
            clamps += 1
            logger.warning(
                "form_derivation_clamp district=%s taluka=%s fiscal_year=%s "
                "category=%s pay_class=%s filled=%s sanctioned=%s",
                district,
                taluka,
                fiscal_year,
                category,
                pay_class,
                filled,
                sanctioned,
            )
        changed = _record_changes(
            db,
            request,
            row,
            DERIVED_POST_EXPENSES_FIELDS,
            {"vacant_posts": vacant},
            context=(
                f"district={district} taluka={taluka} fiscal_year={fiscal_year} "
                f"category={category} pay_class={pay_class}"
            ),
        )
        if changed:
            changed_rows.add((PostExpenses.__tablename__, row.id))
            fields_changed += changed

    status_totals = roll_up_to_status_classes(pay_totals)
    status_contributions = {
        key: ensure_contribution_row(db, PostStatus, consolidated, taluka)
        for key, consolidated in locked.statuses.items()
    }

    for class_type in VALID_CLASS_KEYS:
        filled_row = status_contributions[(class_type, "Filled")]
        vacant_row = status_contributions[(class_type, "Vacant")]
        relevant_expenses = [
            row
            for pay_class, row in expense_contributions.items()
            if PAY_CLASS_TO_STATUS_CLASS[pay_class] == class_type
        ]
        filled_posts = sum(int(row.filled_posts or 0) for row in relevant_expenses)
        vacant_posts = sum(int(row.vacant_posts or 0) for row in relevant_expenses)
        totals = status_totals[class_type]

        filled_values = {"posts": filled_posts}
        vacant_values = {"posts": vacant_posts}
        salary_share = SPLIT_POLICY.filled_share(
            "salary",
            filled_row.salary,
            vacant_row.salary,
            filled_posts,
            vacant_posts,
            None,
        )
        filled_salary = int(round(totals.salary * salary_share))
        filled_values["salary"] = filled_salary
        vacant_values["salary"] = totals.salary - filled_salary

        for measure in DERIVED_POST_STATUS_FIELDS:
            if measure in ("posts", "salary"):
                continue
            total = getattr(totals, measure)
            share = SPLIT_POLICY.filled_share(
                measure,
                getattr(filled_row, measure),
                getattr(vacant_row, measure),
                filled_posts,
                vacant_posts,
                salary_share,
            )
            filled_value = int(round(total * share))
            filled_values[measure] = filled_value
            vacant_values[measure] = total - filled_value

        for status, row, values in (
            ("Filled", filled_row, filled_values),
            ("Vacant", vacant_row, vacant_values),
        ):
            changed = _record_changes(
                db,
                request,
                row,
                DERIVED_POST_STATUS_FIELDS,
                values,
                context=(
                    f"district={district} taluka={taluka} fiscal_year={fiscal_year} "
                    f"category={category} class={class_type} status={status}"
                ),
            )
            if changed:
                changed_rows.add((PostStatus.__tablename__, row.id))
                fields_changed += changed

    db.flush()
    for row in expense_contributions.values():
        consolidate_row(
            db, PostExpenses, district, fiscal_year, _natural_key(row, PostExpenses)
        )
    for row in status_contributions.values():
        consolidate_row(db, PostStatus, district, fiscal_year, _natural_key(row, PostStatus))

    elapsed_ms = (perf_counter() - started) * 1000
    logger.debug(
        "form_derivation district=%s taluka=%s fiscal_year=%s category=%s "
        "b_rows=%s c_rows=%s fields_changed=%s clamps=%s duration_ms=%.2f",
        district,
        taluka,
        fiscal_year,
        category,
        len(expense_contributions),
        len(status_contributions),
        fields_changed,
        clamps,
        elapsed_ms,
    )
    return DerivationResult(len(changed_rows), fields_changed, clamps)


def derive_for_row(db, budget_post_row, request, *, taluka=None) -> DerivationResult:
    """Adapt a source-row identity to one contribution space.

    Normal writes derive the space from authentication. Family deletion passes
    an explicit, server-generated taluka because every deleted sibling must be
    recomputed; request payloads can never select this value.
    """
    if getattr(budget_post_row, TOTAL_SPACE_FLAG, False):
        raise RuntimeError(
            "Cannot derive from lifted total-space row "
            f"{budget_post_row.__tablename__}/{budget_post_row.id}"
        )
    if taluka is None:
        taluka = _writable_taluka_value(
            db,
            budget_post_row.district,
            get_auth_level(request),
            get_auth_unit(request),
        )
    return derive_from_form_d(
        db,
        district=budget_post_row.district,
        fiscal_year=budget_post_row.fiscal_year,
        category=budget_post_row.category,
        taluka=taluka,
        request=request,
    )
