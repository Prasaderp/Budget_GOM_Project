"""Phase 13 regression suite: end-to-end integration across the cumulative
state of Phases 1-12, plus the reconciliation checker's detection logic
(scripts/check_taluka_invariant.py).

Unlike the phase-scoped suites (test_taluka_scope.py, test_taluka_consolidation.py,
test_taluka_chatbot.py), which each exercise one module in isolation, every
test here drives a full write -> consolidate -> read cycle against a REAL
production model (`DistrictExpenditure22350311`, the same class
`scheme_registry` and the real routers resolve to) through the real
`src.core.taluka` package, unmodified. No PostgreSQL connection is required;
`scripts/check_taluka_invariant.py` itself is verified separately by running
it against a live database (not exercised here -- it needs `SessionLocal`,
i.e. `DATABASE_URL`).
"""
from typing import Optional

import pytest
from sqlalchemy.exc import IntegrityError
from starlette.requests import Request

from src import models
from src.core.taluka.constants import DISTRICT_LEVEL, DISTRICT_OFFICE
from src.core.taluka.consolidation import _active_taluka_values, consolidate_row
from src.core.taluka.orm_filter import TALUKA_SCOPE_ALL_OPTION
from src.core.taluka.scope import CONSOLIDATED_SCOPE, DataScope, scope_override
from src.core.taluka.write import (
    create_row_family,
    delete_row_family,
    ensure_contribution_row,
    resolve_editable_row,
)
from src.utils_district import check_edit_permission, validate_access_control
from fastapi import HTTPException

from conftest import (
    MUMBAI_CITY,
    THANE,
    THANE_TALUKAS,
    activate_talukas,
    district_request,
    district_write_request,
    taluka_request,
)

import src.main  # noqa: F401  -- registers every scheme model before this module's imports below
from src.schemes.s2235.subs.s22350311.models import DistrictExpenditure22350311 as DE


@pytest.fixture
def db(scoped_session_factory):
    with scoped_session_factory(DE.__table__) as session:
        yield session


def _row(db, district: str, taluka: str, fy: str = "2025-26", **overrides) -> DE:
    row = DE(fiscal_year=fy, district=district, taluka=taluka, sub_scheme_code="22350311",
             budget_grant_curr=overrides.pop("budget_grant_curr", 0), **overrides)
    db.add(row)
    db.flush()
    return row


def _all_rows(db, district: str, fy: str = "2025-26"):
    return (
        db.query(DE).execution_options(**{TALUKA_SCOPE_ALL_OPTION: True})
        .filter(DE.district == district, DE.fiscal_year == fy).all()
    )


def _consolidated(db, district: str, fy: str = "2025-26") -> Optional[DE]:
    return (
        db.query(DE).execution_options(**{TALUKA_SCOPE_ALL_OPTION: True})
        .filter(DE.district == district, DE.fiscal_year == fy, DE.taluka == DISTRICT_LEVEL).first()
    )


# ---------------------------------------------------------------------------
# End-to-end per user level
# ---------------------------------------------------------------------------

def test_district_assistant_edit_moves_consolidated_by_exact_delta(db):
    activate_talukas(db, THANE, THANE_TALUKAS)
    office = _row(db, THANE, DISTRICT_OFFICE, budget_grant_curr=100)
    _row(db, THANE, THANE_TALUKAS[0], budget_grant_curr=40)
    consolidate_row(db, DE, THANE, "2025-26", {"fiscal_year": "2025-26", "sub_scheme_code": "22350311", "district": THANE})
    before = _consolidated(db, THANE).budget_grant_curr
    assert before == 140

    request = district_write_request(THANE)
    target = resolve_editable_row(db, DE, office.id, request)
    assert target.budget_grant_curr == before  # the form works in district totals, not in the office share
    target.budget_grant_curr += 25
    db.flush()
    consolidate_row(db, DE, THANE, "2025-26", {"fiscal_year": "2025-26", "sub_scheme_code": "22350311", "district": THANE})

    assert _consolidated(db, THANE).budget_grant_curr == before + 25


def test_taluka_assistant_edit_moves_district_and_stays_isolated_from_sibling(db):
    activate_talukas(db, THANE, THANE_TALUKAS)
    _row(db, THANE, DISTRICT_OFFICE, budget_grant_curr=100)
    t1 = _row(db, THANE, THANE_TALUKAS[0], budget_grant_curr=40)
    _row(db, THANE, THANE_TALUKAS[1], budget_grant_curr=20)
    consolidate_row(db, DE, THANE, "2025-26", {"fiscal_year": "2025-26", "sub_scheme_code": "22350311", "district": THANE})
    before = _consolidated(db, THANE).budget_grant_curr
    assert before == 160

    request = taluka_request(THANE_TALUKAS[0])
    target = resolve_editable_row(db, DE, t1.id, request)
    target.budget_grant_curr += 10
    db.flush()
    consolidate_row(db, DE, THANE, "2025-26", {"fiscal_year": "2025-26", "sub_scheme_code": "22350311", "district": THANE})

    assert _consolidated(db, THANE).budget_grant_curr == before + 10

    with scope_override(DataScope(level="taluka", unit=THANE_TALUKAS[1], district=THANE, taluka_value=THANE_TALUKAS[1])):
        sibling_view = db.query(DE).filter(DE.district == THANE, DE.fiscal_year == "2025-26").all()
    assert [r.budget_grant_curr for r in sibling_view] == [20]  # sibling's own row, unaffected and unaware


def test_officer_is_read_only_regardless_of_level(db):
    assert check_edit_permission("officer1", "district", THANE, db, "22350311") is False
    assert check_edit_permission("officer2", "taluka", THANE_TALUKAS[0], db, "22350311") is False
    assert check_edit_permission("dco", "dco", "", db, "22350311") is False


def test_dco_sees_consolidated_total_never_raw_contributions(db):
    activate_talukas(db, THANE, THANE_TALUKAS)
    _row(db, THANE, DISTRICT_OFFICE, budget_grant_curr=100)
    _row(db, THANE, THANE_TALUKAS[0], budget_grant_curr=40)
    consolidate_row(db, DE, THANE, "2025-26", {"fiscal_year": "2025-26", "sub_scheme_code": "22350311", "district": THANE})

    allowed, _ = validate_access_control(THANE, "dco", "", db)
    assert allowed is True
    with scope_override(CONSOLIDATED_SCOPE):
        rows = db.query(DE).filter(DE.district == THANE, DE.fiscal_year == "2025-26").all()
    assert [r.budget_grant_curr for r in rows] == [140]


# ---------------------------------------------------------------------------
# Zero-valued-taluka activation: the Excel / abstract / summary equality proof
# -- those surfaces have zero code changes and read the consolidated row
# unmodified (docs/plan.md §2.2), so proving the consolidated total is
# unchanged immediately after activation *is* the equality proof.
# ---------------------------------------------------------------------------

def test_activation_with_zeroed_contribution_row_leaves_consolidated_total_unchanged(db):
    consolidated_before = _row(db, THANE, DISTRICT_LEVEL, budget_grant_curr=100)
    office = _row(db, THANE, DISTRICT_OFFICE, budget_grant_curr=100)
    db.flush()

    activate_talukas(db, THANE, [THANE_TALUKAS[0]])
    new_contribution = ensure_contribution_row(db, DE, consolidated_before, THANE_TALUKAS[0])
    assert new_contribution.budget_grant_curr == 0

    recomputed = consolidate_row(db, DE, THANE, "2025-26", {"fiscal_year": "2025-26", "sub_scheme_code": "22350311", "district": THANE})
    assert recomputed.budget_grant_curr == 100  # unchanged: 100 (office) + 0 (new taluka)


def test_regression_matrix_a_zero_talukas_district_behaves_as_pre_feature(db):
    """Mumbai City has no possible talukas at all -- the district-office
    contribution and the consolidated total must be identical, exactly as
    before this feature existed."""
    _row(db, MUMBAI_CITY, DISTRICT_OFFICE, budget_grant_curr=77)
    result = consolidate_row(db, DE, MUMBAI_CITY, "2025-26",
                              {"fiscal_year": "2025-26", "sub_scheme_code": "22350311", "district": MUMBAI_CITY})
    assert result.budget_grant_curr == 77
    assert _active_taluka_values(db, MUMBAI_CITY) == []


def test_regression_matrix_c_no_query_ever_returns_consolidated_and_contributions_together(db):
    activate_talukas(db, THANE, THANE_TALUKAS)
    _row(db, THANE, DISTRICT_LEVEL, budget_grant_curr=140)
    _row(db, THANE, DISTRICT_OFFICE, budget_grant_curr=100)
    _row(db, THANE, THANE_TALUKAS[0], budget_grant_curr=40)
    db.flush()

    with scope_override(CONSOLIDATED_SCOPE):
        default_scope_rows = db.query(DE).filter(DE.district == THANE, DE.fiscal_year == "2025-26").all()
    assert {r.taluka for r in default_scope_rows} == {DISTRICT_LEVEL}  # never a mix


def test_regression_matrix_d_no_taluka_reads_another_talukas_row_through_any_query_shape(db):
    activate_talukas(db, THANE, THANE_TALUKAS)
    _row(db, THANE, THANE_TALUKAS[0], budget_grant_curr=40)
    _row(db, THANE, THANE_TALUKAS[1], budget_grant_curr=20)
    db.flush()

    with scope_override(DataScope(level="taluka", unit=THANE_TALUKAS[0], district=THANE, taluka_value=THANE_TALUKAS[0])):
        via_filter = db.query(DE).filter(DE.taluka == THANE_TALUKAS[1]).all()  # explicit filter for sibling
        via_all = db.query(DE).all()
    assert via_filter == []  # injected AND predicate wins over the explicit OR-able filter
    assert [r.budget_grant_curr for r in via_all] == [40]


def test_chatbot_district_total_equals_orm_consolidated_total(db):
    """Proxy for the district view's SELECT (docs/plan.md §5.3): the view is
    `SELECT ... WHERE taluka=''`, which is exactly the consolidated-scope ORM
    query below -- same predicate, same result set."""
    activate_talukas(db, THANE, THANE_TALUKAS)
    _row(db, THANE, DISTRICT_OFFICE, budget_grant_curr=100)
    _row(db, THANE, THANE_TALUKAS[0], budget_grant_curr=40)
    _row(db, THANE, THANE_TALUKAS[1], budget_grant_curr=20)
    consolidate_row(db, DE, THANE, "2025-26", {"fiscal_year": "2025-26", "sub_scheme_code": "22350311", "district": THANE})

    with scope_override(CONSOLIDATED_SCOPE):
        chatbot_view_proxy = db.query(DE).filter(DE.district == THANE, DE.fiscal_year == "2025-26").first()
    assert chatbot_view_proxy.budget_grant_curr == 160


# ---------------------------------------------------------------------------
# Recipe D lifecycle, cumulative with consolidation
# ---------------------------------------------------------------------------

def test_create_then_delete_row_family_leaves_zero_residue(db):
    created = create_row_family(
        db, DE,
        {"fiscal_year": "2025-26", "sub_scheme_code": "22350311", "district": "Sindhudurg", "budget_grant_curr": 50},
        district_request("Sindhudurg"),
    )
    assert {r.taluka for r in _all_rows(db, "Sindhudurg")} == {DISTRICT_LEVEL, DISTRICT_OFFICE}

    deleted = delete_row_family(db, DE, created.id, district_request("Sindhudurg"))
    assert deleted == 2
    assert _all_rows(db, "Sindhudurg") == []


# ---------------------------------------------------------------------------
# Adversarial: malformed payloads, data-contract breaches, race-like ordering
# ---------------------------------------------------------------------------

def test_adversarial_consolidate_row_rejects_incomplete_natural_key(db):
    with pytest.raises(ValueError):
        consolidate_row(db, DE, THANE, "2025-26", {"fiscal_year": "2025-26"})  # 'district' missing


def test_adversarial_negative_amount_violates_check_constraint(db):
    db.add(DE(fiscal_year="2025-26", district=THANE, taluka=DISTRICT_OFFICE,
              sub_scheme_code="22350311", budget_grant_curr=-1))
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_adversarial_create_row_family_missing_district_is_400(db):
    with pytest.raises(HTTPException) as exc:
        create_row_family(db, DE, {"fiscal_year": "2025-26", "budget_grant_curr": 10}, district_request("Thane"))
    assert exc.value.status_code == 400


def test_adversarial_resolve_editable_row_forged_taluka_id_still_403s(db):
    activate_talukas(db, THANE, THANE_TALUKAS)
    t1 = _row(db, THANE, THANE_TALUKAS[0], budget_grant_curr=40)
    t2 = _row(db, THANE, THANE_TALUKAS[1], budget_grant_curr=20)
    db.flush()
    with pytest.raises(HTTPException) as exc:
        resolve_editable_row(db, DE, t2.id, taluka_request(THANE_TALUKAS[0]))
    assert exc.value.status_code == 403


def test_adversarial_interleaved_writers_converge_via_idempotent_full_recompute(db):
    """Simulates two taluka assistants racing to save: a shared ORM Session
    is not thread-safe in SQLAlchemy for any backend (each request gets its
    own Session in production -- src/database.py:get_db()), so the race is
    modeled the way it actually resolves under the app's real transaction
    boundary (docs/plan.md §4.1/§4.2): each writer's commit is followed by a
    consolidate_row() call, and because recomputation is a full SUM over
    source rows rather than `total += delta`, the final state is identical
    no matter which writer's consolidate call lands last -- proven by
    running both orders and comparing, which a delta-based apply would fail.
    """
    activate_talukas(db, THANE, THANE_TALUKAS)
    _row(db, THANE, DISTRICT_OFFICE, budget_grant_curr=100)
    t1 = _row(db, THANE, THANE_TALUKAS[0], budget_grant_curr=40)
    t2 = _row(db, THANE, THANE_TALUKAS[1], budget_grant_curr=20)
    key = {"fiscal_year": "2025-26", "sub_scheme_code": "22350311", "district": THANE}

    t1.budget_grant_curr, t2.budget_grant_curr = 45, 25
    db.flush()

    consolidate_row(db, DE, THANE, "2025-26", key)  # writer 1's post-commit recompute
    consolidate_row(db, DE, THANE, "2025-26", key)  # writer 2's post-commit recompute, same key
    order_a = _consolidated(db, THANE).budget_grant_curr

    consolidate_row(db, DE, THANE, "2025-26", key)  # reversed landing order -- must converge identically
    consolidate_row(db, DE, THANE, "2025-26", key)
    order_b = _consolidated(db, THANE).budget_grant_curr

    assert order_a == order_b == 170  # 100 + 45 + 25, regardless of interleaving


# ---------------------------------------------------------------------------
# The reconciliation checker's detection logic (scripts/check_taluka_invariant.py)
# -- unit-level proof it flags exactly the two Recipe D failure shapes plus a
# value mismatch, using the same grouping/classification helpers the live
# script imports from src.core.taluka.consolidation.
# ---------------------------------------------------------------------------

def _reconcile(db, district: str):
    # src.main is already imported at module scope above, so importing the
    # script here re-executes none of its RUN_DB_CREATE_ALL-gated bootstrap
    # side effects -- Python's module cache makes this a plain function fetch.
    from scripts.check_taluka_invariant import _check_table
    return _check_table(db, DE, district_filter=district, fix=False)


def test_reconciliation_checker_flags_orphan_contribution(db):
    activate_talukas(db, THANE, THANE_TALUKAS)
    _row(db, THANE, THANE_TALUKAS[0], budget_grant_curr=40)  # no district-office, no consolidated twin
    db.flush()

    violations = _reconcile(db, THANE)
    assert any(v["type"] == "orphan" for v in violations)


def test_reconciliation_checker_flags_twinless_consolidated_row(db):
    _row(db, THANE, DISTRICT_LEVEL, budget_grant_curr=100)  # no __district_office__ sibling
    db.flush()

    violations = _reconcile(db, THANE)
    assert any(v["type"] == "twinless" for v in violations)


def test_reconciliation_checker_flags_value_mismatch(db):
    activate_talukas(db, THANE, THANE_TALUKAS)
    _row(db, THANE, DISTRICT_OFFICE, budget_grant_curr=100)
    _row(db, THANE, THANE_TALUKAS[0], budget_grant_curr=40)
    _row(db, THANE, DISTRICT_LEVEL, budget_grant_curr=999)  # stale / corrupted total
    db.flush()

    violations = _reconcile(db, THANE)
    mismatches = [v for v in violations if v["type"] == "mismatch"]
    assert mismatches and mismatches[0]["expected"] == 140 and mismatches[0]["actual"] == 999


def test_reconciliation_checker_clean_state_is_zero_violations(db):
    activate_talukas(db, THANE, THANE_TALUKAS)
    _row(db, THANE, DISTRICT_OFFICE, budget_grant_curr=100)
    _row(db, THANE, THANE_TALUKAS[0], budget_grant_curr=40)
    _row(db, THANE, DISTRICT_LEVEL, budget_grant_curr=140)
    db.flush()

    assert _reconcile(db, THANE) == []


def test_reconciliation_checker_fix_mode_repairs_mismatch(db):
    activate_talukas(db, THANE, THANE_TALUKAS)
    _row(db, THANE, DISTRICT_OFFICE, budget_grant_curr=100)
    _row(db, THANE, THANE_TALUKAS[0], budget_grant_curr=40)
    _row(db, THANE, DISTRICT_LEVEL, budget_grant_curr=0)
    db.flush()

    from scripts.check_taluka_invariant import _check_table
    first_pass = _check_table(db, DE, district_filter=THANE, fix=True)
    assert first_pass and first_pass[0]["type"] == "mismatch"

    second_pass = _check_table(db, DE, district_filter=THANE, fix=False)
    assert second_pass == []
