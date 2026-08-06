"""Phase 6 regression suite: consolidation roll-up and write redirection.

Runs against an in-memory SQLite engine bound to the production declarative
`Base`, so `src.core.taluka.consolidation` and `src.core.taluka.write` run
completely unmodified against a throwaway probe table plus the two real
production tables (`TalukaUserManagement`, `DistrictTalukaSelection`) that
`consolidate_row()` reads to determine which talukas are active. Real
`src.utils_taluka` helpers (district -> taluka name mapping) are used as-is,
so "Mumbai City has zero possible talukas" and "DCO Staff" are exercised
against the actual production data, not a stub.
"""
from urllib.parse import quote

import pytest
from sqlalchemy import Column, Integer, String, UniqueConstraint, create_engine, event
from sqlalchemy.orm import sessionmaker
from starlette.requests import Request

from src import models
from src.core.taluka.constants import DISTRICT_LEVEL, DISTRICT_OFFICE
from src.core.taluka.consolidation import consolidate_district, consolidate_row
from src.core.taluka.models import TalukaScopedMixin
from src.core.taluka.orm_filter import TALUKA_SCOPE_ALL_OPTION, _inject_taluka_scope_filter
from src.core.taluka.write import (
    create_row_family,
    delete_row_family,
    ensure_contribution_row,
    resolve_editable_row,
)
from src.database import Base
from src.config import DCO_STAFF_IDENTIFIER
from fastapi import HTTPException


class _ConsolidationProbe(TalukaScopedMixin, Base):
    __tablename__ = 'test_consolidation_probe'
    id = Column(Integer, primary_key=True)
    fiscal_year = Column(String(7), nullable=False)
    district = Column(String(50), nullable=False)
    amount = Column(Integer, nullable=False, default=0)
    remarks = Column(String(200), nullable=True, default='')
    __table_args__ = (
        UniqueConstraint('fiscal_year', 'district', 'taluka', name='uq_consolidation_probe'),
    )


def _make_request(cookies: dict) -> Request:
    cookie_header = "; ".join(f"{k}={v}" for k, v in cookies.items()).encode()
    scope = {
        "type": "http", "method": "GET", "path": "/",
        "headers": [(b"cookie", cookie_header)] if cookies else [],
        "query_string": b"",
    }
    return Request(scope)


def _district_request(district: str) -> Request:
    return _make_request({'auth_user': 'x', 'auth_level': 'district', 'auth_unit': quote(district)})


def _taluka_request(taluka_unit: str) -> Request:
    return _make_request({'auth_user': 'x', 'auth_level': 'taluka', 'auth_unit': quote(taluka_unit)})


@pytest.fixture
def db():
    engine = create_engine('sqlite:///:memory:')
    TestSessionLocal = sessionmaker(bind=engine)
    event.listen(TestSessionLocal, 'do_orm_execute', _inject_taluka_scope_filter)
    Base.metadata.create_all(engine, tables=[
        _ConsolidationProbe.__table__,
        models.TalukaUserManagement.__table__,
        models.DistrictTalukaSelection.__table__,
    ])
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        event.remove(TestSessionLocal, 'do_orm_execute', _inject_taluka_scope_filter)


def _activate(db, district: str, talukas: list) -> None:
    db.add(models.DistrictTalukaSelection(district=district, selected_talukas=talukas))
    for t in talukas:
        db.add(models.TalukaUserManagement(district=district, taluka_name=t, is_active=True))
    db.flush()


def _row(db, district: str, taluka: str, fiscal_year: str = '2025-26', **kw) -> _ConsolidationProbe:
    row = _ConsolidationProbe(fiscal_year=fiscal_year, district=district, taluka=taluka, **kw)
    db.add(row)
    db.flush()
    return row


def _all_rows(db, district: str, fiscal_year: str = '2025-26'):
    return (
        db.query(_ConsolidationProbe)
        .execution_options(**{TALUKA_SCOPE_ALL_OPTION: True})
        .filter(_ConsolidationProbe.district == district, _ConsolidationProbe.fiscal_year == fiscal_year)
        .all()
    )


# ---------------------------------------------------------------------------
# consolidate_row / consolidate_district
# ---------------------------------------------------------------------------

def test_consolidate_row_single_active_taluka(db):
    _row(db, 'Thane', DISTRICT_OFFICE, amount=40, remarks='HQ')
    _row(db, 'Thane', 'Thane Taluka भिवंडी', amount=35, remarks='taluka note')
    _activate(db, 'Thane', ['Thane Taluka भिवंडी'])

    result = consolidate_row(db, _ConsolidationProbe, 'Thane', '2025-26',
                              {'fiscal_year': '2025-26', 'district': 'Thane'})
    assert result.amount == 75
    assert result.taluka == DISTRICT_LEVEL


def test_consolidate_row_multiple_active_talukas(db):
    _row(db, 'Thane', DISTRICT_OFFICE, amount=40)
    _row(db, 'Thane', 'Thane Taluka भिवंडी', amount=35)
    _row(db, 'Thane', 'Thane Taluka कल्याण', amount=25)
    _activate(db, 'Thane', ['Thane Taluka भिवंडी', 'Thane Taluka कल्याण'])

    result = consolidate_row(db, _ConsolidationProbe, 'Thane', '2025-26',
                              {'fiscal_year': '2025-26', 'district': 'Thane'})
    assert result.amount == 100


def test_consolidate_row_zero_talukas_district_office_only(db):
    # Mumbai City has no possible talukas at all (src.utils_taluka mapping).
    _row(db, 'Mumbai City', DISTRICT_OFFICE, amount=60)

    result = consolidate_row(db, _ConsolidationProbe, 'Mumbai City', '2025-26',
                              {'fiscal_year': '2025-26', 'district': 'Mumbai City'})
    assert result.amount == 60


def test_consolidate_row_dco_staff_has_no_talukas(db):
    _row(db, DCO_STAFF_IDENTIFIER, DISTRICT_OFFICE, amount=15)

    result = consolidate_row(db, _ConsolidationProbe, DCO_STAFF_IDENTIFIER, '2025-26',
                              {'fiscal_year': '2025-26', 'district': DCO_STAFF_IDENTIFIER})
    assert result.amount == 15


def test_consolidate_row_deactivation_excludes_taluka(db):
    _row(db, 'Thane', DISTRICT_OFFICE, amount=40)
    _row(db, 'Thane', 'Thane Taluka भिवंडी', amount=35)
    _row(db, 'Thane', 'Thane Taluka कल्याण', amount=25)
    _activate(db, 'Thane', ['Thane Taluka भिवंडी', 'Thane Taluka कल्याण'])
    consolidate_row(db, _ConsolidationProbe, 'Thane', '2025-26',
                     {'fiscal_year': '2025-26', 'district': 'Thane'})

    mgmt = db.query(models.TalukaUserManagement).filter(
        models.TalukaUserManagement.taluka_name == 'Thane Taluka कल्याण'
    ).first()
    mgmt.is_active = False
    db.flush()

    result = consolidate_row(db, _ConsolidationProbe, 'Thane', '2025-26',
                              {'fiscal_year': '2025-26', 'district': 'Thane'})
    assert result.amount == 75  # 40 + 35, कल्याण's 25 dropped -- row retained, not deleted
    assert len(_all_rows(db, 'Thane')) == 4


def test_consolidate_row_reactivation_restores_contribution(db):
    _row(db, 'Thane', DISTRICT_OFFICE, amount=40)
    _row(db, 'Thane', 'Thane Taluka भिवंडी', amount=35)
    _activate(db, 'Thane', [])  # nothing active yet
    consolidate_row(db, _ConsolidationProbe, 'Thane', '2025-26',
                     {'fiscal_year': '2025-26', 'district': 'Thane'})

    sel = db.query(models.DistrictTalukaSelection).filter(models.DistrictTalukaSelection.district == 'Thane').first()
    sel.selected_talukas = ['Thane Taluka भिवंडी']
    db.add(models.TalukaUserManagement(district='Thane', taluka_name='Thane Taluka भिवंडी', is_active=True))
    db.flush()

    result = consolidate_row(db, _ConsolidationProbe, 'Thane', '2025-26',
                              {'fiscal_year': '2025-26', 'district': 'Thane'})
    assert result.amount == 75


def test_consolidate_row_text_column_from_district_office_never_concatenated(db):
    _row(db, 'Thane', DISTRICT_OFFICE, amount=40, remarks='HQ note')
    _row(db, 'Thane', 'Thane Taluka भिवंडी', amount=35, remarks='taluka note')
    _activate(db, 'Thane', ['Thane Taluka भिवंडी'])

    result = consolidate_row(db, _ConsolidationProbe, 'Thane', '2025-26',
                              {'fiscal_year': '2025-26', 'district': 'Thane'})
    assert result.remarks == 'HQ note'


def test_consolidate_row_is_idempotent_full_recompute(db):
    _row(db, 'Thane', DISTRICT_OFFICE, amount=40)
    taluka_row = _row(db, 'Thane', 'Thane Taluka भिवंडी', amount=35)
    _activate(db, 'Thane', ['Thane Taluka भिवंडी'])
    key = {'fiscal_year': '2025-26', 'district': 'Thane'}

    first = consolidate_row(db, _ConsolidationProbe, 'Thane', '2025-26', key)
    second = consolidate_row(db, _ConsolidationProbe, 'Thane', '2025-26', key)
    assert first.id == second.id
    assert second.amount == 75

    taluka_row.amount = 100
    db.flush()
    third = consolidate_row(db, _ConsolidationProbe, 'Thane', '2025-26', key)
    assert third.amount == 140  # recomputed from source, not 75 + delta


def test_consolidate_district_recomputes_every_natural_key(db):
    for fy in ('2025-26', '2026-27'):
        _row(db, 'Thane', DISTRICT_OFFICE, fiscal_year=fy, amount=40)
        _row(db, 'Thane', 'Thane Taluka भिवंडी', fiscal_year=fy, amount=35)
    _activate(db, 'Thane', ['Thane Taluka भिवंडी'])

    count = consolidate_district(db, _ConsolidationProbe, 'Thane', '2025-26')
    assert count == 1  # only rows matching the given fiscal_year are considered
    row = db.query(_ConsolidationProbe).filter(
        _ConsolidationProbe.taluka == DISTRICT_LEVEL, _ConsolidationProbe.fiscal_year == '2025-26'
    ).first()
    assert row.amount == 75


# ---------------------------------------------------------------------------
# resolve_editable_row -- Recipe R
# ---------------------------------------------------------------------------

@pytest.fixture
def thane_family(db):
    _activate(db, 'Thane', ['Thane Taluka भिवंडी', 'Thane Taluka कल्याण'])
    office = _row(db, 'Thane', DISTRICT_OFFICE, amount=40)
    t1 = _row(db, 'Thane', 'Thane Taluka भिवंडी', amount=35)
    t2 = _row(db, 'Thane', 'Thane Taluka कल्याण', amount=25)
    consolidated = consolidate_row(db, _ConsolidationProbe, 'Thane', '2025-26',
                                    {'fiscal_year': '2025-26', 'district': 'Thane'})
    db.flush()
    return {'office': office, 't1': t1, 't2': t2, 'consolidated': consolidated}


def test_resolve_editable_row_district_user_consolidated_id_resolves_to_office_row(db, thane_family):
    row = resolve_editable_row(db, _ConsolidationProbe, thane_family['consolidated'].id, _district_request('Thane'))
    assert row.id == thane_family['office'].id


def test_resolve_editable_row_district_user_office_id_resolves_to_itself(db, thane_family):
    row = resolve_editable_row(db, _ConsolidationProbe, thane_family['office'].id, _district_request('Thane'))
    assert row.id == thane_family['office'].id


def test_resolve_editable_row_taluka_user_consolidated_id_resolves_to_own_contribution(db, thane_family):
    row = resolve_editable_row(
        db, _ConsolidationProbe, thane_family['consolidated'].id, _taluka_request('Thane Taluka भिवंडी')
    )
    assert row.id == thane_family['t1'].id


def test_resolve_editable_row_taluka_user_own_id_resolves_to_itself(db, thane_family):
    row = resolve_editable_row(db, _ConsolidationProbe, thane_family['t1'].id, _taluka_request('Thane Taluka भिवंडी'))
    assert row.id == thane_family['t1'].id


def test_resolve_editable_row_taluka_user_cannot_reach_sibling_taluka_row(db, thane_family):
    with pytest.raises(HTTPException) as exc:
        resolve_editable_row(db, _ConsolidationProbe, thane_family['t2'].id, _taluka_request('Thane Taluka भिवंडी'))
    assert exc.value.status_code == 403


def test_resolve_editable_row_taluka_user_cannot_reach_district_office_row(db, thane_family):
    with pytest.raises(HTTPException) as exc:
        resolve_editable_row(db, _ConsolidationProbe, thane_family['office'].id, _taluka_request('Thane Taluka भिवंडी'))
    assert exc.value.status_code == 403


def test_resolve_editable_row_404_for_missing_id(db, thane_family):
    with pytest.raises(HTTPException) as exc:
        resolve_editable_row(db, _ConsolidationProbe, 999999, _district_request('Thane'))
    assert exc.value.status_code == 404


def test_error_path_reload_by_id_requires_scope_all_or_taluka_row_vanishes(db, thane_family):
    """Regression for the Phase 10 rollout gap: an update handler's except-block
    reload of `db_item`/`detail_for_form` by raw id, if it omits
    TALUKA_SCOPE_ALL_OPTION, silently loses a taluka caller's own contribution
    row (default scope is taluka=='') and would re-render the error form with
    None instead of the row just being edited.
    """
    taluka_row_id = resolve_editable_row(
        db, _ConsolidationProbe, thane_family['consolidated'].id, _taluka_request('Thane Taluka भिवंडी')
    ).id

    unscoped_reload = db.query(_ConsolidationProbe).filter(_ConsolidationProbe.id == taluka_row_id).first()
    assert unscoped_reload is None  # the bug, reproduced: default scope hides the taluka's own row

    scoped_reload = (
        db.query(_ConsolidationProbe)
        .execution_options(**{TALUKA_SCOPE_ALL_OPTION: True})
        .filter(_ConsolidationProbe.id == taluka_row_id)
        .first()
    )
    assert scoped_reload is not None and scoped_reload.id == taluka_row_id  # the fix


def test_ensure_contribution_row_creates_zeroed_row_lazily(db):
    _activate(db, 'Palghar', ['Palghar Taluka पालघर'])
    consolidated = _row(db, 'Palghar', DISTRICT_LEVEL, amount=50, remarks='seeded')
    db.flush()

    row = ensure_contribution_row(db, _ConsolidationProbe, consolidated, 'Palghar Taluka पालघर')
    assert row.amount == 0
    assert row.district == 'Palghar' and row.fiscal_year == '2025-26'

    again = ensure_contribution_row(db, _ConsolidationProbe, consolidated, 'Palghar Taluka पालघर')
    assert again.id == row.id  # idempotent, no duplicate


# ---------------------------------------------------------------------------
# create_row_family / delete_row_family -- Recipe D
# ---------------------------------------------------------------------------

def test_create_row_family_produces_consolidated_and_office_twin(db):
    result = create_row_family(
        db, _ConsolidationProbe,
        {'fiscal_year': '2025-26', 'district': 'Sindhudurg', 'amount': 50, 'remarks': 'new'},
        _district_request('Sindhudurg'),
    )
    assert result.taluka == DISTRICT_LEVEL
    assert result.amount == 50
    rows = _all_rows(db, 'Sindhudurg')
    assert {r.taluka for r in rows} == {DISTRICT_LEVEL, DISTRICT_OFFICE}


def test_create_row_family_rejects_taluka_caller(db):
    with pytest.raises(HTTPException) as exc:
        create_row_family(
            db, _ConsolidationProbe,
            {'fiscal_year': '2025-26', 'district': 'Thane', 'amount': 10},
            _taluka_request('Thane Taluka भिवंडी'),
        )
    assert exc.value.status_code == 403


def test_delete_row_family_leaves_no_orphan(db, thane_family):
    deleted = delete_row_family(db, _ConsolidationProbe, thane_family['consolidated'].id, _district_request('Thane'))
    assert deleted == 4  # consolidated + office + 2 talukas
    assert _all_rows(db, 'Thane') == []


def test_delete_row_family_rejects_taluka_caller(db, thane_family):
    with pytest.raises(HTTPException) as exc:
        delete_row_family(db, _ConsolidationProbe, thane_family['t1'].id, _taluka_request('Thane Taluka भिवंडी'))
    assert exc.value.status_code == 403
    assert len(_all_rows(db, 'Thane')) == 4  # nothing deleted
