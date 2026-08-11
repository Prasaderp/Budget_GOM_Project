import os
from urllib.parse import quote

os.environ.setdefault("RUN_DB_CREATE_ALL", "false")

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src import models
from src.core.taluka.middleware import TalukaScopeMiddleware
from src.core.taluka.orm_filter import TALUKA_SCOPE_ALL_OPTION, _inject_taluka_scope_filter
from src.core.taluka.constants import DISTRICT_LEVEL, DISTRICT_OFFICE
from src.database import Base, get_db
from src.schemes.common.post_levels.models import PostLevelDetail
from src.schemes.s2029.subs.s20290037 import api_budget_details, ui_budget_details
from src.schemes.s2029.subs.s20290037.models import BudgetPostDetails20290037


FY = "2025-26"
DISTRICT = "Thane"
SUB_SCHEME = "20290037"


def _cookies(role="assistant", level="district", unit=DISTRICT):
    return {
        "auth_user": "test-user",
        "auth_role": role,
        "auth_level": level,
        "auth_unit": quote(unit),
        "selected_scheme": "2029",
        "selected_sub_scheme": SUB_SCHEME,
        "fiscal_year": FY,
    }


def _authenticate(client, cookies):
    client.cookies.clear()
    client.cookies.update(cookies)


def _all_budget_rows(db):
    return (
        db.query(BudgetPostDetails20290037)
        .execution_options(**{TALUKA_SCOPE_ALL_OPTION: True})
        .all()
    )


@pytest.fixture
def http_case():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    event.listen(session_factory, "do_orm_execute", _inject_taluka_scope_filter)
    Base.metadata.create_all(
        engine,
        tables=[
            BudgetPostDetails20290037.__table__,
            PostLevelDetail.__table__,
            models.TalukaUserManagement.__table__,
            models.DistrictTalukaSelection.__table__,
            models.FiscalYear.__table__,
            models.DataFillingPeriod.__table__,
            models.AuditLog.__table__,
        ],
    )
    db = session_factory()
    db.add(models.FiscalYear(year_range=FY, is_active=True, created_by="test"))
    consolidated = BudgetPostDetails20290037(
        district=DISTRICT,
        category="Permanent",
        class_type="Class-3",
        designation="Clerk",
        fiscal_year=FY,
        taluka="",
        sanctioned_posts_curr=4,
    )
    office = BudgetPostDetails20290037(
        district=DISTRICT,
        category="Permanent",
        class_type="Class-3",
        designation="Clerk",
        fiscal_year=FY,
        taluka="__district_office__",
        sanctioned_posts_curr=4,
    )
    db.add_all([consolidated, office])
    db.flush()
    db.add_all(
        [
            PostLevelDetail(
                table_name="budget_post_details_20290037",
                budget_post_id=consolidated.id,
                sub_scheme_code=SUB_SCHEME,
                fiscal_year=FY,
                level_name=name,
                level_order=index,
            )
            for index, name in enumerate(("L1", "L2"), 1)
        ]
    )
    db.commit()

    app = FastAPI()
    app.add_middleware(TalukaScopeMiddleware)
    app.include_router(api_budget_details.router)
    app.include_router(ui_budget_details.router)

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    try:
        yield TestClient(app), db, consolidated.id
    finally:
        db.close()
        event.remove(session_factory, "do_orm_execute", _inject_taluka_scope_filter)
        engine.dispose()


@pytest.fixture
def active_http_case():
    """Real middleware stack with one office and two active taluka contributions."""
    from src.utils_taluka import get_possible_talukas_for_district

    talukas = get_possible_talukas_for_district(DISTRICT)[:2]
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    event.listen(session_factory, "do_orm_execute", _inject_taluka_scope_filter)
    Base.metadata.create_all(
        engine,
        tables=[
            BudgetPostDetails20290037.__table__,
            PostLevelDetail.__table__,
            models.TalukaUserManagement.__table__,
            models.DistrictTalukaSelection.__table__,
            models.FiscalYear.__table__,
            models.DataFillingPeriod.__table__,
            models.AuditLog.__table__,
        ],
    )
    db = session_factory()
    db.add(models.FiscalYear(year_range=FY, is_active=True, created_by="test"))
    db.add(models.DistrictTalukaSelection(district=DISTRICT, selected_talukas=talukas))
    db.add_all(
        [
            models.TalukaUserManagement(
                district=DISTRICT, taluka_name=taluka, is_active=True
            )
            for taluka in talukas
        ]
    )
    rows = [
        BudgetPostDetails20290037(
            district=DISTRICT,
            category="Permanent",
            class_type="Class-3",
            designation="Clerk",
            fiscal_year=FY,
            taluka=DISTRICT_LEVEL,
            sanctioned_posts_curr=6,
        ),
        BudgetPostDetails20290037(
            district=DISTRICT,
            category="Permanent",
            class_type="Class-3",
            designation="Clerk",
            fiscal_year=FY,
            taluka=DISTRICT_OFFICE,
            sanctioned_posts_curr=4,
        ),
        *[
            BudgetPostDetails20290037(
                district=DISTRICT,
                category="Permanent",
                class_type="Class-3",
                designation="Clerk",
                fiscal_year=FY,
                taluka=taluka,
                sanctioned_posts_curr=1,
            )
            for taluka in talukas
        ],
    ]
    db.add_all(rows)
    db.flush()
    db.add_all(
        [
            PostLevelDetail(
                table_name="budget_post_details_20290037",
                budget_post_id=rows[0].id,
                sub_scheme_code=SUB_SCHEME,
                fiscal_year=FY,
                level_name=name,
                level_order=index,
            )
            for index, name in enumerate(("L1", "L2"), 1)
        ]
    )
    db.commit()

    app = FastAPI()
    app.add_middleware(TalukaScopeMiddleware)
    app.include_router(api_budget_details.router)
    app.include_router(ui_budget_details.router)

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    try:
        yield TestClient(app), db, {
            "consolidated": rows[0].id,
            "office": rows[1].id,
            "talukas": {row.taluka: row.id for row in rows[2:]},
        }
    finally:
        db.close()
        event.remove(session_factory, "do_orm_execute", _inject_taluka_scope_filter)
        engine.dispose()


def _form(district=DISTRICT, sanctioned=5):
    return {
        "District": district,
        "Category": "Permanent",
        "Class": "Class-3",
        "Designation": "Clerk",
        "SanctionedPostsPrev1": 0,
        "SanctionedPostsCurr": sanctioned,
        "SpecialPay": 0,
        "BasicPay": 0,
        "GradePay": 0,
        "LocalSupplemetoryAllowance": 0,
        "VehicleAllowance": 0,
        "WashingAllowance": 0,
        "CashAllowance": 0,
        "FootWareAllowanceOther": 0,
        "HraRate": "X",
    }


def test_inline_level_guard_is_http_400_and_preserves_rows(http_case):
    client, db, row_id = http_case
    _authenticate(client, _cookies())
    response = client.post(
        "/ui/s20290037/budget-post-details/api/update-inline",
        data={"id": row_id, "SanctionedPostsCurr": 1},
    )
    assert response.status_code == 400
    assert "2" in response.json()["message"]
    rows = _all_budget_rows(db)
    assert {row.sanctioned_posts_curr for row in rows} == {4}


def test_generic_form_drops_tampered_natural_keys(http_case):
    client, db, row_id = http_case
    _authenticate(client, _cookies())
    response = client.post(
        f"/ui/s20290037/budget-post-details/{row_id}/edit",
        data=_form(district="Palghar"),
        follow_redirects=False,
    )
    assert response.status_code == 303
    rows = _all_budget_rows(db)
    assert {row.district for row in rows} == {DISTRICT}
    assert {row.designation for row in rows} == {"Clerk"}


def test_dco_assistant_can_open_and_save_district_form(http_case):
    client, db, row_id = http_case
    cookies = _cookies(level="dco", unit="KONKAN DIVISION")
    _authenticate(client, cookies)
    response = client.get(f"/ui/s20290037/budget-post-details/{row_id}/edit")
    assert response.status_code == 200
    response = client.post(
        f"/ui/s20290037/budget-post-details/{row_id}/edit",
        data=_form(sanctioned=6),
        follow_redirects=False,
    )
    assert response.status_code == 303
    rows = _all_budget_rows(db)
    assert {row.sanctioned_posts_curr for row in rows} == {6}


def test_district_form_save_moves_consolidated_total_by_exact_delta(active_http_case):
    client, db, ids = active_http_case
    _authenticate(client, _cookies())
    response = client.post(
        f"/ui/s20290037/budget-post-details/{ids['consolidated']}/edit",
        data=_form(sanctioned=8),
        follow_redirects=False,
    )
    assert response.status_code == 303
    rows = {row.taluka: row for row in _all_budget_rows(db)}
    assert rows[DISTRICT_LEVEL].sanctioned_posts_curr == 8
    assert rows[DISTRICT_OFFICE].sanctioned_posts_curr == 6
    assert [rows[t].sanctioned_posts_curr for t in ids["talukas"]] == [1, 1]
    list_response = client.get("/ui/s20290037/budget-post-details?view=edit")
    assert list_response.status_code == 200
    assert "8" in list_response.text


def test_validation_http_400_renders_form_instead_of_500(active_http_case, monkeypatch):
    client, _, ids = active_http_case
    _authenticate(client, _cookies())

    def reject(*_args, **_kwargs):
        raise HTTPException(status_code=400, detail="validation sentinel")

    monkeypatch.setattr(ui_budget_details, "consolidate_row", reject)
    response = client.post(
        f"/ui/s20290037/budget-post-details/{ids['consolidated']}/edit",
        data=_form(sanctioned=7),
    )
    assert response.status_code == 400
    assert "validation sentinel" in response.text


def test_underreported_district_total_has_specific_rendered_reason(active_http_case):
    client, db, ids = active_http_case
    db.query(PostLevelDetail).delete()
    db.commit()
    _authenticate(client, _cookies())
    response = client.post(
        f"/ui/s20290037/budget-post-details/{ids['consolidated']}/edit",
        data=_form(sanctioned=1),
    )
    assert response.status_code == 400
    assert "सक्रिय तालुक्यांनी" in response.text
    error_block = response.text.split('<p class="error">', 1)[1].split("</p>", 1)[0]
    assert "पुन्हा प्रयत्न करा" not in error_block
    rows = {row.taluka: row.sanctioned_posts_curr for row in _all_budget_rows(db)}
    assert rows[DISTRICT_LEVEL] == 6
    assert rows[DISTRICT_OFFICE] == 4


def test_form_and_inline_level_guards_with_active_talukas(active_http_case):
    client, db, ids = active_http_case
    _authenticate(client, _cookies())
    inline = client.post(
        "/ui/s20290037/budget-post-details/api/update-inline",
        data={"id": ids["consolidated"], "SanctionedPostsCurr": 1},
    )
    form = client.post(
        f"/ui/s20290037/budget-post-details/{ids['consolidated']}/edit",
        data=_form(sanctioned=1),
    )
    assert inline.status_code == 400
    assert form.status_code == 400
    assert "2" in inline.json()["message"]
    assert "2" in form.text
    assert {row.sanctioned_posts_curr for row in _all_budget_rows(db)} == {1, 4, 6}


def test_inline_value_survives_following_form_save(http_case):
    client, db, row_id = http_case
    _authenticate(client, _cookies())
    inline = client.post(
        "/ui/s20290037/budget-post-details/api/update-inline",
        data={"id": row_id, "SanctionedPostsCurr": 7},
    )
    form_data = _form()
    form_data.pop("SanctionedPostsCurr")
    form = client.post(
        f"/ui/s20290037/budget-post-details/{row_id}/edit",
        data=form_data,
        follow_redirects=False,
    )
    assert inline.status_code == 200
    assert form.status_code == 303
    assert {row.sanctioned_posts_curr for row in _all_budget_rows(db)} == {7}


def test_apply_aggregates_uses_level_parent_id_and_persists_nonzero_total(active_http_case):
    client, db, ids = active_http_case
    levels = db.query(PostLevelDetail).order_by(PostLevelDetail.level_order).all()
    levels[0].basic_pay = 100
    levels[1].basic_pay = 200
    db.commit()
    _authenticate(client, _cookies())
    response = client.post(
        f"/ui/s20290037/budget-post-details/api/post-levels/{ids['consolidated']}/apply-aggregates"
    )
    assert response.status_code == 200
    assert response.json()["aggregates"]["basic_pay"] == 300
    rows = {row.taluka: row for row in _all_budget_rows(db)}
    assert float(rows[DISTRICT_LEVEL].basic_pay) == 300
    assert float(rows[DISTRICT_OFFICE].basic_pay) == 300


def test_taluka_form_edit_preserves_sibling_contribution(active_http_case):
    client, db, ids = active_http_case
    taluka, sibling = tuple(ids["talukas"])
    before = next(row for row in _all_budget_rows(db) if row.taluka == sibling)
    sibling_snapshot = {column.name: getattr(before, column.name) for column in before.__table__.columns}
    _authenticate(client, _cookies(level="taluka", unit=taluka))
    response = client.post(
        f"/ui/s20290037/budget-post-details/{ids['talukas'][taluka]}/edit",
        data=_form(sanctioned=3),
        follow_redirects=False,
    )
    assert response.status_code == 303
    rows = {row.taluka: row for row in _all_budget_rows(db)}
    assert rows[taluka].sanctioned_posts_curr == 3
    assert {
        column.name: getattr(rows[sibling], column.name)
        for column in rows[sibling].__table__.columns
    } == sibling_snapshot


@pytest.mark.parametrize(
    "cookies",
    [
        _cookies(role="officer1", level="district"),
        _cookies(role="officer2", level="taluka", unit="Thane Taluka blocked"),
        _cookies(role="dco", level="dco", unit="KONKAN DIVISION"),
    ],
)
def test_officers_at_every_level_cannot_post_form(http_case, cookies):
    client, _, row_id = http_case
    _authenticate(client, cookies)
    response = client.post(
        f"/ui/s20290037/budget-post-details/{row_id}/edit",
        data=_form(),
    )
    assert response.status_code == 403


@pytest.mark.parametrize(
    "cookies",
    [
        _cookies(role="officer1"),
        _cookies(role="dco", level="dco", unit="KONKAN DIVISION"),
    ],
)
def test_officers_cannot_apply_post_level_aggregates(cookies):
    from src.main import app

    client = TestClient(app)
    _authenticate(client, cookies)
    response = client.post(
        "/ui/s20530028/budget-post-details/api/post-levels/1/apply-aggregates"
    )
    assert response.status_code == 403
