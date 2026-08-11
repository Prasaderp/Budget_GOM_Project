from types import SimpleNamespace

import pytest

from src.core.taluka.write import strip_protected_update_fields
from src.schemes.common.post_levels.schemas import AggregatedTotals
from src.schemes.common.post_levels.service import PostLevelService
from src.schemes.s2053.subs.s20530028.models import BudgetPostDetails
from src.schemes.s2053.subs.s20530028.post_expenses.dto.post_expenses_dto import (
    PostExpensesFormUpdateDTO,
)
from src.schemes.s2053.subs.s20530028.post_expenses.services.post_expenses_service import (
    PostExpensesService,
)


def _aggregates() -> AggregatedTotals:
    return AggregatedTotals(
        count=2,
        special_pay=11,
        basic_pay=1200,
        grade_pay=130,
        local_supplementary_allowance=14,
        vehicle_allowance=15,
        washing_allowance=16,
        cash_allowance=17,
        footwear_allowance_other=18,
        dearness_allowance=851,
        hra_total=399,
        grand_total=2671,
    )


def test_apply_aggregates_keeps_levels_id_separate_from_write_target(monkeypatch):
    service = PostLevelService(SimpleNamespace())
    parent = SimpleNamespace(fiscal_year="2025-26", sub_scheme_code="20530028")
    calls = []
    monkeypatch.setattr(
        service,
        "calculate_aggregates",
        lambda *args: calls.append(args) or _aggregates(),
    )

    result = service.apply_aggregates_to_budget_post(
        41, parent, "20530028", "budget_post_details_20530028", "2025-26"
    )

    assert calls == [
        (41, "20530028", "budget_post_details_20530028", "2025-26")
    ]
    assert parent.basic_pay == 1200
    assert parent.grade_pay == 130
    assert parent.special_pay == 11
    assert result["grand_total"] == 2671


@pytest.mark.parametrize(
    ("fiscal_year", "sub_scheme_code"),
    [("2024-25", "20530028"), ("2025-26", "forged")],
)
def test_apply_aggregates_rejects_parent_identity_breach(
    fiscal_year, sub_scheme_code
):
    service = PostLevelService(SimpleNamespace())
    parent = SimpleNamespace(
        fiscal_year=fiscal_year, sub_scheme_code=sub_scheme_code
    )

    with pytest.raises(ValueError, match="identity"):
        service.apply_aggregates_to_budget_post(
            41, parent, "20530028", "budget_post_details_20530028", "2025-26"
        )


def test_strip_protected_update_fields_drops_complete_row_identity():
    payload = {
        "id": 999,
        "scheme_code": "forged",
        "sub_scheme_code": "forged",
        "fiscal_year": "2099-00",
        "taluka": "forged",
        "district": "forged",
        "category": "forged",
        "class_type": "forged",
        "designation": "forged",
        "basic_pay": 2500,
    }

    assert strip_protected_update_fields(BudgetPostDetails, payload) == {
        "basic_pay": 2500
    }


def test_post_expense_form_returns_sync_intent_without_bulk_commit():
    record = SimpleNamespace(
        fiscal_year="2025-26",
        district="Thane",
        category="Permanent",
        class_type="Class-3",
        filled_posts=1,
        vacant_posts=1,
        medical_expenses=0,
        festival_advance=0,
        swagram_maharashtra_darshan=0,
        other=0,
        nps=0,
        seventh_pay_commission_difference=0,
        seventh_pay_commission_difference_nps=0,
    )
    repository = SimpleNamespace(
        get_by_id=lambda *_: record,
        update=lambda value: value,
    )
    service = PostExpensesService(repository)

    updated, sync_update = service.update_form(
        1,
        "20530028",
        PostExpensesFormUpdateDTO(
            district="Thane",
            category="Permanent",
            class_type="Class-3",
            medical_expenses=25,
            festival_advance=10,
        ),
    )

    assert updated is record
    assert sync_update == {"medical_expenses": 25, "festival_advance": 10}
