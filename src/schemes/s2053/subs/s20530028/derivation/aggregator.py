"""Read-only aggregation of Form D rows into Form B and Form C cells."""

from dataclasses import dataclass, fields
from decimal import Decimal
import logging

from src.core.taluka.orm_filter import TALUKA_SCOPE_ALL_OPTION

from ..config import CLASS_1_2_KEY, CLASS_3_KEY, CLASS_4_KEY
from ..models import BudgetPostDetails
from .mapping import MEASURE_MAP, pay_class_for

logger = logging.getLogger(__name__)

PAY_CLASSES = ('1', '2', '3', '4')


@dataclass(frozen=True)
class CellTotals:
    sanctioned: int = 0
    salary: int = 0
    grade_pay: int = 0
    special_pay: int = 0
    dearness_allowance: int = 0
    local_supplementary_allowance: int = 0
    house_rent_allowance: int = 0
    travel_allowance: int = 0
    other: int = 0

    def __add__(self, other: 'CellTotals') -> 'CellTotals':
        if not isinstance(other, CellTotals):
            return NotImplemented
        return CellTotals(
            **{
                field.name: getattr(self, field.name) + getattr(other, field.name)
                for field in fields(self)
            }
        )


def _empty_accumulator() -> dict[str, Decimal | int]:
    return {
        'sanctioned': 0,
        **{field: Decimal(0) if field == 'salary' else 0 for field, _ in MEASURE_MAP},
    }


def aggregate_pay_classes(
    db,
    *,
    taluka: str,
    district: str,
    fiscal_year: str,
    category: str,
    da_rate: float,
) -> dict[str, CellTotals]:
    """Aggregate one exact contribution space with one unscoped ORM query."""
    rows = (
        db.query(BudgetPostDetails)
        .execution_options(**{TALUKA_SCOPE_ALL_OPTION: True})
        .filter(
            BudgetPostDetails.taluka == taluka,
            BudgetPostDetails.district == district,
            BudgetPostDetails.fiscal_year == fiscal_year,
            BudgetPostDetails.category == category,
        )
        .all()
    )
    totals = {pay_class: _empty_accumulator() for pay_class in PAY_CLASSES}

    for row in rows:
        try:
            pay_class = pay_class_for(row.class_type, row.designation)
        except ValueError:
            logger.warning(
                "Skipping Form D row with unsupported class_type %r: id=%s designation=%r",
                row.class_type,
                row.id,
                row.designation,
            )
            continue

        cell = totals[pay_class]
        cell['sanctioned'] += int(row.sanctioned_posts_curr or 0)
        for measure, extractor in MEASURE_MAP:
            value = extractor(row, da_rate) if measure == 'dearness_allowance' else extractor(row)
            if measure == 'salary':
                cell[measure] += Decimal(value or 0)
            else:
                cell[measure] += int(value or 0)

    return {
        pay_class: CellTotals(
            **{
                **cell,
                'salary': int(round(cell['salary'])),
            }
        )
        for pay_class, cell in totals.items()
    }


def roll_up_to_status_classes(
    pay_class_totals: dict[str, CellTotals],
) -> dict[str, CellTotals]:
    """Collapse Form B's pay classes into Form C's class vocabulary."""
    empty = CellTotals()
    return {
        CLASS_1_2_KEY: pay_class_totals.get('1', empty) + pay_class_totals.get('2', empty),
        CLASS_3_KEY: pay_class_totals.get('3', empty),
        CLASS_4_KEY: pay_class_totals.get('4', empty),
    }
