import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from src import models as core_models
from src.core import secure_crud
from src.core.derivation.registry import register, run_for
from src.core.taluka.constants import DISTRICT_LEVEL, DISTRICT_OFFICE, TOTAL_SPACE_FLAG
from src.core.taluka.orm_filter import _inject_taluka_scope_filter
from src.database import Base
from src.schemes.s2053.subs.s20530028.config import (
    CLASS_1_2_KEY,
    CLASS_3_KEY,
    CLASS_4_KEY,
)
from src.schemes.s2053.subs.s20530028.derivation import service
from src.schemes.s2053.subs.s20530028.derivation.service import (
    acquire_derivation_locks,
    derive_for_row,
    derive_from_form_d,
)
from src.schemes.s2053.subs.s20530028.models import (
    BudgetPostDetails,
    PostExpenses,
    PostStatus,
)
from src.core.taluka.write import writable_scope
from src.schemes.s2053.subs.s20530028.post_expenses.dto.post_expenses_dto import (
    PostExpensesUpdateDTO,
)
from src.schemes.s2053.subs.s20530028.post_expenses.repositories.post_expenses_repository import (
    PostExpensesRepository,
)
from src.schemes.s2053.subs.s20530028.post_expenses.services.post_expenses_service import (
    PostExpensesService,
)
from src.schemes.s2053.subs.s20530028.post_expenses.utils.validators import (
    validate_filled_against_sanctioned,
)
from src.schemes.s2053.subs.s20530028.post_expenses.controllers import (
    api_controller as post_expenses_api,
)
from src.schemes.s2053.subs.s20530028.post_expenses.controllers.api_controller import (
    api_update_inline as update_post_expenses_inline,
)
from src.schemes.s2053.subs.s20530028.post_status.controllers import (
    api_controller as post_status_api,
    ui_controller as post_status_ui,
)
from src.schemes.s2053.subs.s20530028.post_status.controllers.api_controller import (
    api_update_inline as update_post_status_inline,
)
from src.schemes.s2053.subs.s20530028.post_status.controllers.ui_controller import (
    ui_update_post_status as update_post_status_form,
)
from src.schemes.s2053.subs.s20530028.post_status.repositories.post_status_repository import (
    PostStatusRepository,
)
from src.schemes.s2053.subs.s20530028.post_status.services.post_status_service import (
    PostStatusService,
)
from src.schemes.s2053.subs.s20530028.derivation import allocation as allocation_module
from src.schemes.s2053.subs.s20530028.config import ALLOCATABLE_POST_STATUS_FIELDS
from src.schemes.s2053.subs.s20530028.router_api import router as scheme_api_router
from src.schemes.s2053.subs.s20530028.schemas import (
    PostExpensesUpdate,
    PostStatusUpdate,
)

from conftest import activate_talukas, district_write_request


DISTRICT = "Mumbai City"
FISCAL_YEAR = "2025-26"
CATEGORY = "Permanent"
TALUKA = "Mumbai City Taluka test"


@pytest.fixture
def db(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    session_factory = sessionmaker(bind=engine)
    event.listen(session_factory, "do_orm_execute", _inject_taluka_scope_filter)
    Base.metadata.create_all(
        engine,
        tables=[
            core_models.TalukaUserManagement.__table__,
            core_models.DistrictTalukaSelection.__table__,
            core_models.AuditLog.__table__,
            BudgetPostDetails.__table__,
            PostExpenses.__table__,
            PostStatus.__table__,
        ],
    )
    session = session_factory()
    monkeypatch.setattr(service, "get_da_rate", lambda _db, _fy: 0.64)
    try:
        yield session
    finally:
        session.close()
        event.remove(session_factory, "do_orm_execute", _inject_taluka_scope_filter)
        engine.dispose()


def _identity(taluka):
    return dict(
        scheme_code="2053",
        sub_scheme_code="20530028",
        fiscal_year=FISCAL_YEAR,
        district=DISTRICT,
        category=CATEGORY,
        taluka=taluka,
    )


def _seed_target_families(db, *, filled_class_1=2):
    for pay_class in ("1", "2", "3", "4"):
        for taluka in (DISTRICT_LEVEL, DISTRICT_OFFICE):
            db.add(
                PostExpenses(
                    class_type=pay_class,
                    filled_posts=filled_class_1 if pay_class == "1" else 0,
                    vacant_posts=91 if pay_class == "1" else 0,
                    medical_expenses=101,
                    festival_advance=102,
                    swagram_maharashtra_darshan=103,
                    seventh_pay_commission_difference_nps=104.5,
                    nps=105.5,
                    seventh_pay_commission_difference=106.5,
                    other=107,
                    **_identity(taluka),
                )
            )
    for class_type in (CLASS_1_2_KEY, CLASS_3_KEY, CLASS_4_KEY):
        for status in ("Filled", "Vacant"):
            for taluka in (DISTRICT_LEVEL, DISTRICT_OFFICE):
                db.add(
                    PostStatus(
                        class_type=class_type,
                        status=status,
                        posts=0,
                        salary=0,
                        grade_pay=0,
                        special_pay=0,
                        dearness_allowance=0,
                        local_supplementary_allowance=0,
                        house_rent_allowance=0,
                        travel_allowance=0,
                        other=0,
                        **_identity(taluka),
                    )
                )
    db.flush()


def _seed_form_d(db):
    row = BudgetPostDetails(
        class_type=CLASS_1_2_KEY,
        designation="Collector",
        sanctioned_posts_prev1=99,
        sanctioned_posts_curr=3,
        special_pay=5,
        basic_pay=100,
        grade_pay=20,
        local_supplementary_allowance=7,
        vehicle_allowance=8,
        washing_allowance=1,
        cash_allowance=2,
        footwear_allowance_other=3,
        hra_rate="X",
        **_identity(DISTRICT_OFFICE),
    )
    db.add(row)
    db.flush()
    return row


def _seed_consolidated_form_d(db):
    source = _seed_form_d(db)
    consolidated = BudgetPostDetails(
        class_type=source.class_type,
        designation=source.designation,
        sanctioned_posts_prev1=source.sanctioned_posts_prev1,
        sanctioned_posts_curr=source.sanctioned_posts_curr,
        special_pay=source.special_pay,
        basic_pay=source.basic_pay,
        grade_pay=source.grade_pay,
        local_supplementary_allowance=source.local_supplementary_allowance,
        vehicle_allowance=source.vehicle_allowance,
        washing_allowance=source.washing_allowance,
        cash_allowance=source.cash_allowance,
        footwear_allowance_other=source.footwear_allowance_other,
        hra_rate=source.hra_rate,
        **_identity(DISTRICT_LEVEL),
    )
    db.add(consolidated)
    db.flush()
    return source, consolidated


def _unscoped(db, model):
    return db.query(model).execution_options(taluka_scope_all=True)


def _expense(db, pay_class, taluka=DISTRICT_OFFICE):
    return _unscoped(db, PostExpenses).filter_by(
        district=DISTRICT,
        fiscal_year=FISCAL_YEAR,
        category=CATEGORY,
        class_type=pay_class,
        taluka=taluka,
    ).one()


def _status(db, class_type, status, taluka=DISTRICT_OFFICE):
    return _unscoped(db, PostStatus).filter_by(
        district=DISTRICT,
        fiscal_year=FISCAL_YEAR,
        category=CATEGORY,
        class_type=class_type,
        status=status,
        taluka=taluka,
    ).one()


def test_writer_propagates_only_connected_fields_and_is_idempotent(db):
    _seed_target_families(db)
    source = _seed_form_d(db)
    source_before = {column.name: getattr(source, column.name) for column in source.__table__.columns}
    expense_before = {
        field: getattr(_expense(db, "1"), field)
        for field in (
            "filled_posts",
            "medical_expenses",
            "festival_advance",
            "swagram_maharashtra_darshan",
            "seventh_pay_commission_difference_nps",
            "nps",
            "seventh_pay_commission_difference",
            "other",
        )
    }

    first = derive_from_form_d(
        db,
        district=DISTRICT,
        fiscal_year=FISCAL_YEAR,
        category=CATEGORY,
        taluka=DISTRICT_OFFICE,
    )

    assert _expense(db, "1").vacant_posts == 1
    filled = _status(db, CLASS_1_2_KEY, "Filled")
    vacant = _status(db, CLASS_1_2_KEY, "Vacant")
    assert (filled.posts, vacant.posts) == (2, 1)
    assert (filled.salary, vacant.salary) == (67, 33)
    assert filled.salary + vacant.salary == 100
    assert filled.grade_pay + vacant.grade_pay == 20
    assert filled.special_pay + vacant.special_pay == 5
    assert filled.dearness_allowance + vacant.dearness_allowance == 77
    assert filled.house_rent_allowance + vacant.house_rent_allowance == 36
    assert filled.travel_allowance + vacant.travel_allowance == 8
    assert filled.other + vacant.other == 6
    assert expense_before == {field: getattr(_expense(db, "1"), field) for field in expense_before}
    assert source_before == {
        column.name: getattr(source, column.name) for column in source.__table__.columns
    }
    assert first.rows_written == 3
    assert first.fields_changed > 0

    second = derive_from_form_d(
        db,
        district=DISTRICT,
        fiscal_year=FISCAL_YEAR,
        category=CATEGORY,
        taluka=DISTRICT_OFFICE,
    )
    assert second.rows_written == 0
    assert second.fields_changed == 0


def test_writer_clamps_only_vacancy_when_filled_exceeds_sanctioned(db, caplog):
    _seed_target_families(db, filled_class_1=8)
    _seed_form_d(db)
    with caplog.at_level("WARNING"):
        result = derive_from_form_d(
            db,
            district=DISTRICT,
            fiscal_year=FISCAL_YEAR,
            category=CATEGORY,
            taluka=DISTRICT_OFFICE,
        )
    assert _expense(db, "1").filled_posts == 8
    assert _expense(db, "1").vacant_posts == 0
    assert result.clamps == 1
    assert "form_derivation_clamp" in caplog.text


def test_missing_consolidated_family_fails_before_source_scan(db, monkeypatch):
    _seed_target_families(db)
    _seed_form_d(db)
    missing = _unscoped(db, PostStatus).filter_by(
        taluka=DISTRICT_LEVEL,
        class_type=CLASS_4_KEY,
        status="Vacant",
    ).one()
    db.delete(missing)
    db.flush()
    scanned = False

    def fail_if_scanned(*_args, **_kwargs):
        nonlocal scanned
        scanned = True

    monkeypatch.setattr(service, "aggregate_pay_classes", fail_if_scanned)
    with pytest.raises(RuntimeError, match="Missing consolidated"):
        derive_from_form_d(
            db,
            district=DISTRICT,
            fiscal_year=FISCAL_YEAR,
            category=CATEGORY,
            taluka=DISTRICT_OFFICE,
        )
    assert scanned is False


def test_lock_order_is_form_b_then_form_c(db):
    _seed_target_families(db)
    statements = []

    def capture(_conn, _cursor, statement, _parameters, _context, _many):
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append(statement.lower())

    event.listen(db.bind, "before_cursor_execute", capture)
    try:
        locks = acquire_derivation_locks(db, DISTRICT, FISCAL_YEAR, CATEGORY)
    finally:
        event.remove(db.bind, "before_cursor_execute", capture)
    assert tuple(locks.expenses) == ("1", "2", "3", "4")
    assert tuple(locks.statuses) == tuple(
        (class_type, status)
        for class_type in (CLASS_1_2_KEY, CLASS_3_KEY, CLASS_4_KEY)
        for status in ("Filled", "Vacant")
    )
    assert "post_expenses_20530028" in statements[0]
    assert "post_status_20530028" in statements[1]


def test_total_space_guard_prevents_mixed_share_scan(db):
    lifted = SimpleNamespace(
        id=7,
        __tablename__="budget_post_details_20530028",
        district=DISTRICT,
        fiscal_year=FISCAL_YEAR,
        category=CATEGORY,
    )
    setattr(lifted, TOTAL_SPACE_FLAG, True)
    with pytest.raises(RuntimeError, match="lifted total-space row"):
        derive_for_row(db, lifted, district_write_request(DISTRICT))


def test_controller_adapter_uses_row_year_and_authenticated_office_space(db, monkeypatch):
    _seed_target_families(db)
    row = _seed_form_d(db)
    captured = {}

    def capture(_db, **kwargs):
        captured.update(kwargs)
        return "result"

    request = district_write_request(DISTRICT)
    monkeypatch.setattr(service, "derive_from_form_d", capture)
    assert derive_for_row(db, row, request) == "result"
    assert captured.pop("request") is request
    assert captured == {
        "district": DISTRICT,
        "fiscal_year": FISCAL_YEAR,
        "category": CATEGORY,
        "taluka": DISTRICT_OFFICE,
    }


def test_controller_adapter_accepts_only_server_selected_explicit_space(db, monkeypatch):
    captured = {}
    target = SimpleNamespace(
        district=DISTRICT,
        fiscal_year=FISCAL_YEAR,
        category=CATEGORY,
    )

    def capture(_db, **kwargs):
        captured.update(kwargs)
        return "result"

    monkeypatch.setattr(service, "derive_from_form_d", capture)
    request = district_write_request(DISTRICT)
    assert derive_for_row(db, target, request, taluka="Thane Taluka कल्याण") == "result"
    assert captured["taluka"] == "Thane Taluka कल्याण"
    assert captured["request"] is request


def test_form_b_filled_validation_uses_consolidated_form_d_total(db):
    _seed_target_families(db)
    _seed_consolidated_form_d(db)
    record = _expense(db, "1")

    assert validate_filled_against_sanctioned(db, record, 3) == (True, None)
    valid, message = validate_filled_against_sanctioned(db, record, 4)
    assert valid is False
    assert "मंजूर पदांपेक्षा (3) जास्त" in message


def test_form_b_service_ignores_caller_vacancy_and_rejects_excess_filled(db):
    _seed_target_families(db)
    _seed_consolidated_form_d(db)
    record = _expense(db, "1")
    service_under_test = PostExpensesService(PostExpensesRepository(db))

    def dto(filled):
        return PostExpensesUpdateDTO(
            id=record.id,
            filled_posts=filled,
            vacant_posts=999_999,
            medical_expenses=1,
            festival_advance=2,
            swagram_maharashtra_darshan=3,
            nps_unified=4,
            other=5,
        )

    with writable_scope(record):
        service_under_test.update_inline(dto(3), "20530028")
    assert record.filled_posts == 3
    assert record.vacant_posts == 91

    with writable_scope(record), pytest.raises(ValueError, match="मंजूर पदांपेक्षा"):
        service_under_test.update_inline(dto(4), "20530028")


def test_derive_audit_is_persisted_in_callers_transaction(db):
    _seed_target_families(db)
    _seed_form_d(db)
    derive_from_form_d(
        db,
        district=DISTRICT,
        fiscal_year=FISCAL_YEAR,
        category=CATEGORY,
        taluka=DISTRICT_OFFICE,
        request=district_write_request(DISTRICT),
    )
    actions = [row.action for row in db.query(core_models.AuditLog).all()]
    assert actions and set(actions) == {"DERIVE"}


def test_writer_never_commits_and_all_derived_changes_roll_back(db):
    _seed_target_families(db)
    _seed_form_d(db)
    db.commit()

    derive_from_form_d(
        db,
        district=DISTRICT,
        fiscal_year=FISCAL_YEAR,
        category=CATEGORY,
        taluka=DISTRICT_OFFICE,
        request=district_write_request(DISTRICT),
    )
    assert _expense(db, "1").vacant_posts == 1
    assert db.query(core_models.AuditLog).count() > 0

    db.rollback()
    assert _expense(db, "1").vacant_posts == 91
    assert _status(db, CLASS_1_2_KEY, "Filled").salary == 0
    assert db.query(core_models.AuditLog).count() == 0


def test_core_registry_is_noop_for_unregistered_models_and_rejects_conflicts():
    class Unregistered:
        pass

    class Registered:
        pass

    hook = lambda db, row, request: (db, row, request)
    register(Registered, hook)
    assert run_for("db", Unregistered, "row", "request") is None
    assert run_for("db", Registered, "row", "request") == ("db", "row", "request")
    register(Registered, hook)
    with pytest.raises(RuntimeError, match="already registered"):
        register(Registered, lambda *_args: None)


def test_core_registry_forwards_server_context_to_registered_hook():
    class RegisteredWithContext:
        pass

    hook = lambda db, row, request, **context: context
    register(RegisteredWithContext, hook)
    assert run_for(
        "db",
        RegisteredWithContext,
        "row",
        "request",
        taluka="server-selected",
    ) == {"taluka": "server-selected"}


def test_form_c_put_route_stays_suppressed():
    """The generic PUT cannot maintain Filled + Vacant == total, so it is not registered.

    Its hook slot in secure_crud.update_item is shared with create_item and
    delete_item, whose call shapes carry no class_type/status (plan Phase 8 box).
    """
    methods = {
        method
        for route in scheme_api_router.routes
        if route.path == "/api/schemes/20530028/post-status/{id}"
        for method in route.methods
    }
    assert "GET" in methods
    assert "PUT" not in methods


def test_public_update_schemas_exclude_derived_fields():
    assert PostStatusUpdate.model_fields == {}
    with pytest.raises(ValidationError):
        PostStatusUpdate.model_validate({"salary": 1})

    update = PostExpensesUpdate(filled_posts=2, medical_expenses=3)
    assert update.model_dump(exclude_unset=True) == {
        "filled_posts": 2,
        "medical_expenses": 3,
    }
    with pytest.raises(ValidationError):
        PostExpensesUpdate.model_validate({"vacant_posts": 1})


def test_templates_lock_derived_fields_and_only_those():
    """Read-only iff derived (plan AMENDMENT 1). Nothing wider, nothing narrower."""
    root = Path(__file__).resolve().parents[1] / "templates/schemes/s2053/subs/s20530028"
    status_form = (root / "post_status_form.html").read_text(encoding="utf-8")
    status_list = (root / "post_status_list.html").read_text(encoding="utf-8")
    expenses_form = (root / "post_expenses_form.html").read_text(encoding="utf-8")
    expenses_list = (root / "post_expenses_list.html").read_text(encoding="utf-8")

    def tag(markup, field):
        return next(line for line in markup.splitlines() if f'name="{field}"' in line)

    # Form C: posts is derived from Form B (LINK 3) and is never writable.
    assert "readonly" in tag(status_form, "Posts")
    # The eight money measures are writable exactly on the Filled row.
    for field in (
        "Salary",
        "GradePay",
        "SpecialPay",
        "DearnessAllowance",
        "LocalSupplemetoryAllowance",
        "HouseRentAllowance",
        "TravelAllowance",
        "Other",
    ):
        assert "{% if not is_filled %}readonly" in tag(status_form, field)
    assert "{% if is_filled %}<button type=\"submit\"" in status_form

    # The quick-edit block is back, with the same two narrowings.
    assert "inlineEditForm" in status_list
    assert "api/update-inline" in status_list
    assert "readonly" in tag(status_list, "Posts")
    assert "applyAllocationLock" in status_list

    # Form B: only रिक्त पदे is derived. Everything else stays editable.
    assert "readonly" in tag(expenses_form, "VacantPosts")
    for field in (
        "FilledPosts",
        "MedicalExpenses",
        "FestivalAdvance",
        "SwagramMaharashtraDarshan",
        "Other",
        "NPSUnified",
    ):
        assert "readonly" not in tag(expenses_form, field)
    vacant_offset = expenses_list.index('id="inline_vacant"')
    assert "readonly" in expenses_list[vacant_offset : vacant_offset + 220]
    filled_offset = expenses_list.index('id="inline_filled"')
    assert "readonly" not in expenses_list[filled_offset : filled_offset + 220]


def test_dry_run_reconciliation_reports_drift_without_persisting(db):
    import scripts.reconcile_form_derivation as reconcile

    _seed_target_families(db)
    _seed_form_d(db)
    group = (DISTRICT, FISCAL_YEAR, CATEGORY, DISTRICT_OFFICE)

    changes, result = reconcile._reconcile_group(db, group, fix=False)
    assert changes
    assert result.fields_changed > 0
    assert _status(db, CLASS_1_2_KEY, "Filled").salary == 0
    assert _expense(db, "1").vacant_posts == 91

    changes, _ = reconcile._reconcile_group(db, group, fix=True)
    assert changes
    assert _status(db, CLASS_1_2_KEY, "Filled").salary == 67
    assert _expense(db, "1").vacant_posts == 1


def test_mixed_hra_rates_are_derived_per_contribution_then_consolidated(db):
    _seed_target_families(db)
    office = _seed_form_d(db)
    activate_talukas(db, DISTRICT, [TALUKA])
    db.add(
        BudgetPostDetails(
            class_type=CLASS_1_2_KEY,
            designation="Collector",
            sanctioned_posts_prev1=0,
            sanctioned_posts_curr=1,
            special_pay=0,
            basic_pay=200,
            grade_pay=0,
            local_supplementary_allowance=0,
            vehicle_allowance=0,
            washing_allowance=0,
            cash_allowance=0,
            footwear_allowance_other=0,
            hra_rate="Z",
            **_identity(TALUKA),
        )
    )
    db.flush()

    derive_from_form_d(
        db,
        district=DISTRICT,
        fiscal_year=FISCAL_YEAR,
        category=CATEGORY,
        taluka=DISTRICT_OFFICE,
    )
    derive_from_form_d(
        db,
        district=DISTRICT,
        fiscal_year=FISCAL_YEAR,
        category=CATEGORY,
        taluka=TALUKA,
    )

    office_total = sum(
        _status(db, CLASS_1_2_KEY, status).house_rent_allowance
        for status in ("Filled", "Vacant")
    )
    taluka_total = sum(
        _status(db, CLASS_1_2_KEY, status, TALUKA).house_rent_allowance
        for status in ("Filled", "Vacant")
    )
    consolidated_total = sum(
        _status(db, CLASS_1_2_KEY, status, DISTRICT_LEVEL).house_rent_allowance
        for status in ("Filled", "Vacant")
    )
    assert office.hra_rate == "X"
    assert (office_total, taluka_total, consolidated_total) == (36, 20, 56)


@pytest.mark.parametrize("policy_name", ["preserve", "post_ratio"])
def test_every_split_policy_preserves_filled_plus_vacant_totals(db, monkeypatch, policy_name):
    from src.schemes.s2053.subs.s20530028.derivation.split_policy import (
        PostRatioSplit,
        PreserveShareSplit,
    )

    _seed_target_families(db)
    _seed_form_d(db)
    policy = PreserveShareSplit() if policy_name == "preserve" else PostRatioSplit()
    monkeypatch.setattr(service, "SPLIT_POLICY", policy)
    derive_from_form_d(
        db,
        district=DISTRICT,
        fiscal_year=FISCAL_YEAR,
        category=CATEGORY,
        taluka=DISTRICT_OFFICE,
    )

    filled = _status(db, CLASS_1_2_KEY, "Filled")
    vacant = _status(db, CLASS_1_2_KEY, "Vacant")
    expected = {
        "posts": 3,
        "salary": 100,
        "grade_pay": 20,
        "special_pay": 5,
        "dearness_allowance": 77,
        "local_supplementary_allowance": 7,
        "house_rent_allowance": 36,
        "travel_allowance": 8,
        "other": 6,
    }
    assert {
        field: getattr(filled, field) + getattr(vacant, field)
        for field in expected
    } == expected


def test_form_b_filled_edit_rederives_form_c_in_the_same_transaction(db, monkeypatch):
    _seed_target_families(db)
    _, source_total = _seed_consolidated_form_d(db)
    expense_total = _expense(db, "1", DISTRICT_LEVEL)
    source_before = source_total.sanctioned_posts_curr

    monkeypatch.setattr(post_expenses_api, "check_edit_permission_for_scheme", lambda *_: True)
    monkeypatch.setattr(post_expenses_api, "check_data_filling_allowed", lambda *_: (True, None))
    monkeypatch.setattr(
        post_expenses_api, "get_scheme_from_cookies", lambda *_: ("2053", "20530028")
    )
    monkeypatch.setattr(post_expenses_api.CacheService, "invalidate_scheme_cache", lambda *_: None)
    monkeypatch.setattr(post_expenses_api.AuditService, "log_audit_async", lambda *_: None)

    response = asyncio.run(
        update_post_expenses_inline(
            district_write_request(DISTRICT),
            id=expense_total.id,
            FilledPosts=1,
            VacantPosts=999_999,
            MedicalExpenses=101,
            FestivalAdvance=102,
            SwagramMaharashtraDarshan=103,
            NPSUnified=104,
            Other=107,
            service=PostExpensesService(PostExpensesRepository(db)),
        )
    )

    assert response.status_code == 200
    assert (
        _status(db, CLASS_1_2_KEY, "Filled", DISTRICT_LEVEL).posts,
        _status(db, CLASS_1_2_KEY, "Vacant", DISTRICT_LEVEL).posts,
    ) == (1, 2)
    assert _expense(db, "1", DISTRICT_LEVEL).vacant_posts == 2
    assert source_total.sanctioned_posts_curr == source_before


def test_source_family_delete_rederives_every_active_contribution_space(db, monkeypatch):
    _seed_target_families(db)
    _, source_total = _seed_consolidated_form_d(db)
    talukas = ("Mumbai City Taluka one", "Mumbai City Taluka two")
    activate_talukas(db, DISTRICT, list(talukas))
    for taluka in talukas:
        db.add(
            BudgetPostDetails(
                class_type=CLASS_1_2_KEY,
                designation="Collector",
                sanctioned_posts_prev1=0,
                sanctioned_posts_curr=1,
                special_pay=0,
                basic_pay=10,
                grade_pay=0,
                local_supplementary_allowance=0,
                vehicle_allowance=0,
                washing_allowance=0,
                cash_allowance=0,
                footwear_allowance_other=0,
                hra_rate="X",
                **_identity(taluka),
            )
        )
    db.flush()
    for taluka in (DISTRICT_OFFICE, *talukas):
        derive_from_form_d(
            db,
            district=DISTRICT,
            fiscal_year=FISCAL_YEAR,
            category=CATEGORY,
            taluka=taluka,
        )
    assert _status(db, CLASS_1_2_KEY, "Filled", DISTRICT_LEVEL).salary > 0

    monkeypatch.setattr(secure_crud, "_require_auth", lambda *_: "tester")
    monkeypatch.setattr(secure_crud, "_check_write_permission", lambda *_: None)
    monkeypatch.setattr(secure_crud, "_check_district_access", lambda *_: None)
    monkeypatch.setattr(secure_crud, "_log_audit", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(secure_crud, "_serialize_values", lambda *_: {})
    delete_endpoint = next(
        route.endpoint
        for route in scheme_api_router.routes
        if route.path == "/api/schemes/20530028/budget-post-details/{id}"
        and "DELETE" in route.methods
    )
    response = delete_endpoint(
        request=district_write_request(DISTRICT), id=source_total.id, db=db
    )

    assert response.status_code == 204
    assert (
        _unscoped(db, BudgetPostDetails)
        .filter_by(district=DISTRICT, designation="Collector")
        .count()
        == 0
    )
    for taluka in (DISTRICT_OFFICE, *talukas, DISTRICT_LEVEL):
        filled = _status(db, CLASS_1_2_KEY, "Filled", taluka)
        vacant = _status(db, CLASS_1_2_KEY, "Vacant", taluka)
        assert filled.salary + vacant.salary == 0
        assert vacant.posts == 0
        assert filled.posts == _expense(db, "1", taluka).filled_posts


def _allocation_env(monkeypatch, db):
    from src.schemes.s2053.subs.s20530028.post_status.services import (
        post_status_service as post_status_service_module,
    )

    monkeypatch.setattr(allocation_module, "get_da_rate", lambda _db, _fy: 0.64)
    monkeypatch.setattr(
        post_status_service_module, "check_edit_permission_for_scheme", lambda *_: True
    )
    monkeypatch.setattr(
        post_status_service_module, "check_data_filling_allowed", lambda *_: (True, None)
    )
    monkeypatch.setattr(
        post_status_service_module, "validate_access_control", lambda *_: (True, None)
    )
    monkeypatch.setattr(
        post_status_api, "get_scheme_from_cookies", lambda *_: ("2053", "20530028")
    )
    monkeypatch.setattr(
        post_status_ui, "get_scheme_from_cookies", lambda *_: ("2053", "20530028")
    )
    monkeypatch.setattr(
        post_status_ui, "check_data_filling_allowed", lambda *_: (True, None)
    )
    return PostStatusService(db)


# Calling the handler directly bypasses FastAPI's Form() resolution, so every
# parameter must be supplied explicitly (same convention as the Form B tests).
_ALLOCATION_FORM_FIELDS = {
    "Salary": "salary",
    "GradePay": "grade_pay",
    "SpecialPay": "special_pay",
    "DearnessAllowance": "dearness_allowance",
    "LocalSupplemetoryAllowance": "local_supplementary_allowance",
    "HouseRentAllowance": "house_rent_allowance",
    "TravelAllowance": "travel_allowance",
    "Other": "other",
}


def _run_allocation(db, row_id, **overrides):
    row = _unscoped(db, PostStatus).filter_by(id=row_id).one()
    payload = {
        name: overrides.get(name, getattr(row, column))
        for name, column in _ALLOCATION_FORM_FIELDS.items()
    }
    return asyncio.run(
        update_post_status_inline(
            district_write_request(DISTRICT),
            id=row_id,
            service=PostStatusService(db),
            **payload,
        )
    )


def _seeded_cell(db):
    """One Form D row + zeroed Form B/C families, propagated once."""
    _seed_target_families(db, filled_class_1=1)
    source, _ = _seed_consolidated_form_d(db)
    derive_from_form_d(
        db,
        district=DISTRICT,
        fiscal_year=FISCAL_YEAR,
        category=CATEGORY,
        taluka=DISTRICT_OFFICE,
    )
    db.flush()
    return source


def test_allocation_edit_preserves_the_form_d_total(monkeypatch, db):
    """I1: writing Filled leaves Filled + Vacant equal to Form D's class total."""
    _seeded_cell(db)
    _allocation_env(monkeypatch, db)
    filled = _status(db, CLASS_1_2_KEY, "Filled", DISTRICT_LEVEL)
    totals = {
        field: getattr(filled, field)
        + getattr(_status(db, CLASS_1_2_KEY, "Vacant", DISTRICT_LEVEL), field)
        for field in ALLOCATABLE_POST_STATUS_FIELDS
    }
    assert totals["salary"] == 100

    response = _run_allocation(
        db,
        filled.id,
        Salary=30,
        GradePay=6,
        SpecialPay=2,
        DearnessAllowance=25,
        LocalSupplemetoryAllowance=3,
        HouseRentAllowance=11,
        TravelAllowance=4,
        Other=2,
    )
    assert response.status_code == 200

    new_filled = _status(db, CLASS_1_2_KEY, "Filled", DISTRICT_LEVEL)
    new_vacant = _status(db, CLASS_1_2_KEY, "Vacant", DISTRICT_LEVEL)
    assert new_filled.salary == 30
    for field, total in totals.items():
        assert getattr(new_filled, field) + getattr(new_vacant, field) == total


def test_allocation_survives_an_unchanged_form_d_save(monkeypatch, db):
    """PreserveShareSplit's fixed point is what makes the allocation durable."""
    _seeded_cell(db)
    _allocation_env(monkeypatch, db)
    filled = _status(db, CLASS_1_2_KEY, "Filled", DISTRICT_LEVEL)
    _run_allocation(db, filled.id, Salary=30, DearnessAllowance=25)

    before = {
        field: getattr(_status(db, CLASS_1_2_KEY, "Filled", DISTRICT_LEVEL), field)
        for field in ALLOCATABLE_POST_STATUS_FIELDS
    }
    derive_from_form_d(
        db,
        district=DISTRICT,
        fiscal_year=FISCAL_YEAR,
        category=CATEGORY,
        taluka=DISTRICT_OFFICE,
    )
    db.flush()
    after = {
        field: getattr(_status(db, CLASS_1_2_KEY, "Filled", DISTRICT_LEVEL), field)
        for field in ALLOCATABLE_POST_STATUS_FIELDS
    }
    assert after == before


def test_vacant_rows_and_posts_stay_locked(monkeypatch, db):
    _seeded_cell(db)
    _allocation_env(monkeypatch, db)

    vacant = _status(db, CLASS_1_2_KEY, "Vacant", DISTRICT_LEVEL)
    response = _run_allocation(db, vacant.id, Salary=1)
    assert response.status_code == 409

    filled = _status(db, CLASS_1_2_KEY, "Filled", DISTRICT_LEVEL)
    posts_before = filled.posts
    _run_allocation(db, filled.id, Salary=10)
    assert _status(db, CLASS_1_2_KEY, "Filled", DISTRICT_LEVEL).posts == posts_before

    # `posts` is not even accepted as an input on either write path.
    import inspect

    for handler in (update_post_status_inline, update_post_status_form):
        assert "Posts" not in inspect.signature(handler).parameters


def test_over_allocation_is_rejected_not_clamped(monkeypatch, db):
    _seeded_cell(db)
    _allocation_env(monkeypatch, db)
    filled = _status(db, CLASS_1_2_KEY, "Filled", DISTRICT_LEVEL)
    salary_before = filled.salary

    response = _run_allocation(db, filled.id, Salary=999_999)
    assert response.status_code == 400
    body = response.body.decode("utf-8")
    assert "प्रपत्र ड" in body
    assert _status(db, CLASS_1_2_KEY, "Filled", DISTRICT_LEVEL).salary == salary_before


def test_rebalance_refuses_a_lifted_row(db):
    """The section 4.2 trap, one form further along."""
    _seed_target_families(db)
    row = _status(db, CLASS_1_2_KEY, "Filled")
    setattr(row, TOTAL_SPACE_FLAG, True)
    with pytest.raises(RuntimeError):
        allocation_module.rebalance_status_split(db, row, None)


def test_form_b_unconnected_expenses_are_never_written_by_form_c(monkeypatch, db):
    """Section 2.6 pinned from the Form C side."""
    _seeded_cell(db)
    _allocation_env(monkeypatch, db)
    before = {
        pay_class: (
            _expense(db, pay_class).medical_expenses,
            _expense(db, pay_class).festival_advance,
            _expense(db, pay_class).swagram_maharashtra_darshan,
            _expense(db, pay_class).nps,
            _expense(db, pay_class).other,
            _expense(db, pay_class).filled_posts,
        )
        for pay_class in ("1", "2", "3", "4")
    }
    filled = _status(db, CLASS_1_2_KEY, "Filled", DISTRICT_LEVEL)
    _run_allocation(db, filled.id, Salary=30, Other=2)

    for pay_class, snapshot in before.items():
        assert (
            _expense(db, pay_class).medical_expenses,
            _expense(db, pay_class).festival_advance,
            _expense(db, pay_class).swagram_maharashtra_darshan,
            _expense(db, pay_class).nps,
            _expense(db, pay_class).other,
            _expense(db, pay_class).filled_posts,
        ) == snapshot
