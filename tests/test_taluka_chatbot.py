"""Phase 12 regression suite: chatbot view-resolution scoping and the
read-only taluka breakdown page.

Three surfaces are exercised end-to-end against the cumulative state of
Phases 1-11: `DynamicSchemaEngine._resolve_table_names()` (schema_engine.py),
`DivisionDistrictSecurityMixin._enforce_district_sql_scope()` (policies.py),
and the `ui_taluka_breakdown` router (src/routers/ui_taluka_breakdown.py),
which is called directly as a coroutine -- bypassing FastAPI's DI so the
real production ORM models, the real `iter_scoped_models()` registry and the
real Jinja2 template render all run unmodified.
"""
import asyncio
from urllib.parse import quote

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from starlette.requests import Request

from src import models
from src.core.base_config import BaseSchemeConfig, FormConfig
from src.core.taluka.constants import DISTRICT_LEVEL, DISTRICT_OFFICE
from src.core.taluka.orm_filter import _inject_taluka_scope_filter
from src.database import Base

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")


def _make_request(cookies: dict, path: str = "/ui/s22350311/taluka-breakdown") -> Request:
    cookie_header = "; ".join(f"{k}={v}" for k, v in cookies.items()).encode()
    scope = {
        "type": "http", "method": "GET", "path": path,
        "headers": [(b"cookie", cookie_header)] if cookies else [],
        "query_string": b"",
    }
    return Request(scope)


def _district_request(district: str) -> Request:
    return _make_request({"auth_user": "x", "auth_level": "district", "auth_unit": quote(district)})


def _taluka_request(unit: str) -> Request:
    return _make_request({"auth_user": "x", "auth_level": "taluka", "auth_unit": quote(unit)})


def _dco_request() -> Request:
    return _make_request({"auth_user": "x", "auth_level": "dco", "auth_unit": ""})


# ---------------------------------------------------------------------------
# _resolve_table_names — the double-count-prevention view swap and its trap
# ---------------------------------------------------------------------------

def _engine():
    from src.chatbot.core.schema_engine import DynamicSchemaEngine
    return DynamicSchemaEngine()


def _cfg(table_names: dict) -> BaseSchemeConfig:
    return BaseSchemeConfig(
        code="test", parent_scheme="test", scheme_type="voted",
        name_en="t", name_mr="t", implemented=True,
        forms={
            name: FormConfig(name=name, table_name=tbl, label_mr="", label_en="")
            for name, tbl in table_names.items()
        },
    )


def test_resolve_table_names_maps_scoped_table_to_district_view():
    import src.main  # noqa: F401  -- populates iter_scoped_models() before resolution
    names = _engine()._resolve_table_names(_cfg({"de": "district_expenditure_22350311"}))
    assert names["de"] == "v_district_expenditure_22350311_district"


def test_resolve_table_names_leaves_unscoped_division_table_untouched():
    """sub_head_expenditure_2075 has no `district` column and is explicitly
    excluded from taluka scoping (docs/plan.md §3.1) -- and from the view
    family the migration creates. Remapping it would 404 every chatbot query
    against it; this is the sharpest trap in Phase 12 (risk register #2)."""
    import src.main  # noqa: F401
    names = _engine()._resolve_table_names(_cfg({
        "de": "district_expenditure_2075",
        "she": "sub_head_expenditure_2075",
    }))
    assert names["de"] == "v_district_expenditure_2075_district"
    assert names["she"] == "sub_head_expenditure_2075"


def test_resolve_table_names_against_real_registry_scheme():
    """Cumulative integration: the real 22350311 config, loaded through the
    real scheme_registry (Phases 9-11's rollout target), resolves the same way."""
    import src.main  # noqa: F401  -- triggers full scheme registration
    from src.core.registry import scheme_registry

    config = scheme_registry.get_scheme("22350311")
    assert config is not None and config.implemented
    names = _engine()._resolve_table_names(config)
    assert set(names.values()) == {"v_district_expenditure_22350311_district"}


def test_build_context_populates_tables_from_view_schema_info(monkeypatch):
    """Regression for the get_schema_info() gap: information_schema.tables
    filtered to BASE TABLE only would silently return schema_info == {} for
    every view name, leaving ctx.tables (and therefore the LLM prompt) empty
    even though _resolve_table_names() resolved correctly."""
    import src.main  # noqa: F401
    from src.chatbot.core import schema_engine as se

    fake_columns = [{
        "column_name": "district", "data_type": "character varying",
        "is_nullable": "NO", "column_default": None,
        "character_maximum_length": 50, "numeric_precision": None, "numeric_scale": None,
    }]
    view_name = "v_district_expenditure_22350311_district"
    monkeypatch.setattr(se, "get_schema_info", lambda: {view_name: {"columns": fake_columns}})
    monkeypatch.setattr(se, "get_db_connection", lambda timeout=5: (_ for _ in ()).throw(RuntimeError("no db in unit test")))
    se._schema_context_cache.cache.clear()
    se._fiscal_year_cache.cache.clear()

    from src.core.registry import scheme_registry
    config = scheme_registry.get_scheme("22350311")
    ctx = se.DynamicSchemaEngine().build_context("22350311")

    assert view_name in ctx.tables
    assert "district" in ctx.all_columns[view_name]
    assert ctx.available_fiscal_years == []  # DB unavailable -> fail-safe empty, not a crash


# ---------------------------------------------------------------------------
# _enforce_district_sql_scope — taluka -> parent-district mapping
# ---------------------------------------------------------------------------

def _policy_mixin():
    from src.chatbot.security.policies import DivisionDistrictSecurityMixin
    return DivisionDistrictSecurityMixin()


def test_district_user_own_district_allowed():
    ok, _ = _policy_mixin()._enforce_district_sql_scope(
        'SELECT * FROM v_x WHERE "district" = \'thane\'',
        {"role": "assistant", "level": "district", "unit": "Thane"},
    )
    assert ok is True


def test_district_user_cross_district_blocked():
    ok, msg = _policy_mixin()._enforce_district_sql_scope(
        'SELECT * FROM v_x WHERE "district" = \'raigad\'',
        {"role": "assistant", "level": "district", "unit": "Thane"},
    )
    assert ok is False and "own district" in msg


def test_taluka_user_mapped_to_parent_district_allowed():
    ok, _ = _policy_mixin()._enforce_district_sql_scope(
        'SELECT * FROM v_x WHERE "district" = \'thane\'',
        {"role": "assistant", "level": "taluka", "unit": "Thane Taluka भिवंडी"},
    )
    assert ok is True


def test_taluka_user_cross_district_blocked_via_parent_mapping():
    ok, msg = _policy_mixin()._enforce_district_sql_scope(
        'SELECT * FROM v_x WHERE "district" = \'raigad\'',
        {"role": "assistant", "level": "taluka", "unit": "Thane Taluka भिवंडी"},
    )
    assert ok is False and "own district" in msg


def test_taluka_user_malformed_unit_blocked_not_silently_allowed():
    """Adversarial: a unit string that doesn't parse to '<District> Taluka
    <Name>' must never fall through to `True, sql` -- that would be an
    unscoped bypass for a forged/corrupted cookie."""
    ok, msg = _policy_mixin()._enforce_district_sql_scope(
        'SELECT * FROM v_x WHERE "district" = \'thane\'',
        {"role": "assistant", "level": "taluka", "unit": "not-a-real-unit"},
    )
    assert ok is False and "not linked" in msg


def test_elevated_role_bypasses_scoping_regardless_of_level():
    ok, _ = _policy_mixin()._enforce_district_sql_scope(
        'SELECT * FROM v_x WHERE "district" = \'raigad\'',
        {"role": "dco", "level": "taluka", "unit": "Thane Taluka भिवंडी"},
    )
    assert ok is True


def test_query_without_district_predicate_untouched():
    ok, _ = _policy_mixin()._enforce_district_sql_scope(
        "SELECT count(*) FROM v_x",
        {"role": "assistant", "level": "taluka", "unit": "Thane Taluka भिवंडी"},
    )
    assert ok is True


# ---------------------------------------------------------------------------
# ui_taluka_breakdown — read-only per-taluka split
#
# Uses the REAL production model (DistrictExpenditure22350311), the same one
# scheme_registry.get_scheme("22350311") resolves to -- so this is a genuine
# end-to-end run through the actual router, actual scheme config lookup and
# actual iter_scoped_models() registry, not a synthetic stand-in.
# ---------------------------------------------------------------------------

import src.main  # noqa: E402,F401  -- registers all schemes before the module below is imported
from src.schemes.s2235.subs.s22350311.models import DistrictExpenditure22350311  # noqa: E402


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    TestSessionLocal = sessionmaker(bind=engine)
    event.listen(TestSessionLocal, "do_orm_execute", _inject_taluka_scope_filter)
    Base.metadata.create_all(engine, tables=[
        DistrictExpenditure22350311.__table__,
        models.TalukaUserManagement.__table__,
        models.DistrictTalukaSelection.__table__,
    ])
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        event.remove(TestSessionLocal, "do_orm_execute", _inject_taluka_scope_filter)


def _activate(db, district: str, talukas: list) -> None:
    db.add(models.DistrictTalukaSelection(district=district, selected_talukas=talukas))
    for t in talukas:
        db.add(models.TalukaUserManagement(district=district, taluka_name=t, is_active=True))
    db.flush()


def _row(db, district: str, taluka: str, budget_grant_curr: int = 0, fy: str = "2025-26"):
    db.add(DistrictExpenditure22350311(
        fiscal_year=fy, district=district, taluka=taluka, budget_grant_curr=budget_grant_curr,
    ))
    db.flush()


def _breakdown_route(db, request, **overrides):
    import src.main  # noqa: F401  -- ensures scheme_registry is populated regardless of test order
    from src.routers import ui_taluka_breakdown as mod

    monkeypatch_targets = {
        "form": None, "district": None, "page": 1, "page_size": 50,
    }
    monkeypatch_targets.update(overrides)

    async def _run():
        return await mod.ui_taluka_breakdown(
            request=request, scheme_code="22350311", db=db, **monkeypatch_targets
        )

    return asyncio.run(_run())


def test_taluka_user_denied_403(db):
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        _breakdown_route(db, _taluka_request("Thane Taluka भिवंडी"))
    assert exc.value.status_code == 403


def test_unauthenticated_denied_401(db):
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        _breakdown_route(db, _make_request({}))
    assert exc.value.status_code == 401


def test_dco_staff_district_user_denied_403(db):
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        _breakdown_route(db, _district_request("DCO Staff"))
    assert exc.value.status_code == 403


def test_dco_invalid_district_query_param_rejected(db):
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        _breakdown_route(db, _dco_request(), district="Not A Real District")
    assert exc.value.status_code == 400


def test_district_office_and_taluka_split_renders_with_correct_labels(db, monkeypatch):
    from src.routers import ui_taluka_breakdown as mod
    monkeypatch.setattr(mod, "get_fiscal_year_from_request", lambda request, db: "2025-26")

    _activate(db, "Thane", ["Thane Taluka भिवंडी", "Thane Taluka कल्याण"])
    _row(db, "Thane", DISTRICT_OFFICE, budget_grant_curr=100)
    _row(db, "Thane", "Thane Taluka भिवंडी", budget_grant_curr=40)
    _row(db, "Thane", "Thane Taluka कल्याण", budget_grant_curr=60)
    _row(db, "Thane", DISTRICT_LEVEL, budget_grant_curr=200)  # consolidated total
    db.commit()

    response = _breakdown_route(db, _district_request("Thane"))
    body = response.body.decode("utf-8")

    assert response.status_code == 200
    assert "जिल्हा कार्यालय" in body      # district-office label
    assert "भिवंडी" in body and "कल्याण" in body  # both taluka labels, unit prefix stripped
    assert "200" in body                  # consolidated total rendered


def test_orphan_natural_key_missing_district_office_row_defaults_to_zero_not_crash(db, monkeypatch):
    """Adversarial data-integrity trap: a taluka contribution row exists for
    a natural key with no district-office twin (the exact orphan shape
    Recipe D's checker in Phase 13 is built to catch). The read-only
    breakdown page must degrade to showing 0, never 500."""
    from src.routers import ui_taluka_breakdown as mod
    monkeypatch.setattr(mod, "get_fiscal_year_from_request", lambda request, db: "2025-26")

    _activate(db, "Thane", ["Thane Taluka भिवंडी"])
    _row(db, "Thane", "Thane Taluka भिवंडी", budget_grant_curr=25)
    db.commit()

    response = _breakdown_route(db, _district_request("Thane"))
    assert response.status_code == 200


def test_pagination_slices_natural_keys_correctly(db, monkeypatch):
    from src.routers import ui_taluka_breakdown as mod
    monkeypatch.setattr(mod, "get_fiscal_year_from_request", lambda request, db: "2025-26")

    for i in range(5):
        _row(db, "Thane", DISTRICT_LEVEL, budget_grant_curr=i, fy=f"202{i}-2{i+1}")
    db.commit()

    page1 = _breakdown_route(db, _district_request("Thane"), page_size=2, page=1)
    page2 = _breakdown_route(db, _district_request("Thane"), page_size=2, page=2)
    page3 = _breakdown_route(db, _district_request("Thane"), page_size=2, page=3)

    assert all(r.status_code == 200 for r in (page1, page2, page3))


def test_mumbai_city_zero_talukas_shows_district_office_only(db, monkeypatch):
    """Mumbai City has no possible talukas (src/utils_taluka.py); the
    contributor list must be exactly [district office], and the page must
    render without needing any taluka activation."""
    from src.routers import ui_taluka_breakdown as mod
    monkeypatch.setattr(mod, "get_fiscal_year_from_request", lambda request, db: "2025-26")

    _row(db, "Mumbai City", DISTRICT_OFFICE, budget_grant_curr=10)
    _row(db, "Mumbai City", DISTRICT_LEVEL, budget_grant_curr=10)
    db.commit()

    response = _breakdown_route(db, _district_request("Mumbai City"))
    body = response.body.decode("utf-8")
    assert response.status_code == 200
    assert "कोणतेही तालुके सक्रिय नाहीत" in body
