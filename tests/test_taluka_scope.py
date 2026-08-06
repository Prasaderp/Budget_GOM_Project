"""Phase 1-2 regression suite: scope primitives, the scoped-model mixin, and
the ORM read-isolation interception point.

No PostgreSQL connection is required. Phase 1 tests are pure Python /
in-memory SQLAlchemy metadata inspection; the Phase 2 isolation matrix below
runs against an in-memory SQLite engine with two throwaway scoped models —
it reuses the production `_inject_taluka_scope_filter` function itself
(src/core/taluka/orm_filter.py), bound to a throwaway sessionmaker, so this
is a test of the real interception logic, not a reimplementation of it.
"""
from urllib.parse import quote

import pytest
from sqlalchemy import (
    Column,
    Integer,
    String,
    UniqueConstraint,
    create_engine,
    event,
    func,
    select,
)
from sqlalchemy.orm import declarative_base, sessionmaker
from starlette.requests import Request

from src.core.taluka.constants import (
    DISTRICT_LEVEL,
    DISTRICT_OFFICE,
    RESERVED_TALUKA_VALUES,
)
from src.core.taluka.models import TalukaScopedMixin, natural_key_columns
from src.core.taluka.scope import (
    CONSOLIDATED_SCOPE,
    resolve_scope_from_request,
    scope_override,
)
from src.database import Base

from src.schemes.s0029.subs.s0029.models import DistrictRevenue0029
from src.schemes.s2045.common.district_expenditure.base_models import (
    create_district_expenditure_model,
)
from src.schemes.s2075.models import DistrictExpenditure2075
from src.schemes.s2235.subs.s22350311.models import DistrictExpenditure22350311
from src.schemes.s2053.subs.s20530028.models import BudgetPostDetails20530028


def _make_request(cookies: dict) -> Request:
    cookie_header = "; ".join(f"{k}={v}" for k, v in cookies.items()).encode()
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [(b"cookie", cookie_header)] if cookies else [],
        "query_string": b"",
    }
    return Request(scope)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

def test_reserved_values_are_district_level_and_district_office():
    assert RESERVED_TALUKA_VALUES == {DISTRICT_LEVEL, DISTRICT_OFFICE}


def test_district_level_is_empty_string_not_null_sentinel():
    # UNIQUE constraints treat NULL as distinct per row in PostgreSQL, so the
    # consolidated row must be a real, equal, empty string.
    assert DISTRICT_LEVEL == ''


def test_reserved_values_are_frozen():
    with pytest.raises(AttributeError):
        RESERVED_TALUKA_VALUES.add('something')


# ---------------------------------------------------------------------------
# TalukaScopedMixin — the @declared_attr trap
# ---------------------------------------------------------------------------

def test_mixin_produces_a_real_mapped_column_not_a_shared_class_attribute():
    class _ProbeA(TalukaScopedMixin, Base):
        __tablename__ = 'test_taluka_probe_a'
        id = Column(Integer, primary_key=True)

    class _ProbeB(TalukaScopedMixin, Base):
        __tablename__ = 'test_taluka_probe_b'
        id = Column(Integer, primary_key=True)

    assert 'taluka' in _ProbeA.__table__.c
    assert 'taluka' in _ProbeB.__table__.c
    # Each subclass must own its own Column instance (declared_attr semantics),
    # not share one Column object across tables.
    assert _ProbeA.__table__.c.taluka is not _ProbeB.__table__.c.taluka
    assert _ProbeA.__table__.c.taluka.default.arg == DISTRICT_LEVEL


# ---------------------------------------------------------------------------
# natural_key_columns() — across the 5 structurally distinct model shapes
# ---------------------------------------------------------------------------

def test_natural_key_columns_four_table_family_shape():
    assert natural_key_columns(BudgetPostDetails20530028) == (
        'fiscal_year', 'district', 'category', 'class_type', 'designation',
    )


def test_natural_key_columns_standalone_district_expenditure_shape():
    assert natural_key_columns(DistrictExpenditure22350311) == (
        'fiscal_year', 'sub_scheme_code', 'district',
    )


def test_natural_key_columns_s2045_factory_shape():
    Model = create_district_expenditure_model(
        table_name='test_district_expenditure_probe',
        scheme_code='9999',
        sub_scheme_code='99990001',
    )
    assert natural_key_columns(Model) == ('fiscal_year', 'sub_scheme_code', 'district')


def test_natural_key_columns_section_based_shape():
    assert natural_key_columns(DistrictRevenue0029) == (
        'fiscal_year', 'sub_scheme_code', 'table_section_code', 'district',
    )


def test_natural_key_columns_s2075_district_level_shape():
    assert natural_key_columns(DistrictExpenditure2075) == (
        'fiscal_year', 'sub_scheme_code', 'district',
    )


def test_natural_key_columns_raises_on_zero_unique_constraints():
    class _NoKey(Base):
        __tablename__ = 'test_taluka_no_natural_key'
        id = Column(Integer, primary_key=True)
        name = Column(String(50))

    with pytest.raises(ValueError):
        natural_key_columns(_NoKey)


def test_natural_key_columns_raises_on_multiple_unique_constraints():
    class _TwoKeys(Base):
        __tablename__ = 'test_taluka_two_natural_keys'
        id = Column(Integer, primary_key=True)
        a = Column(String(50))
        b = Column(String(50))
        __table_args__ = (
            UniqueConstraint('a', name='uq_a'),
            UniqueConstraint('b', name='uq_b'),
        )

    with pytest.raises(ValueError):
        natural_key_columns(_TwoKeys)


# ---------------------------------------------------------------------------
# resolve_scope_from_request()
# ---------------------------------------------------------------------------

def test_scope_for_dco_is_consolidated():
    scope = resolve_scope_from_request(_make_request({'auth_user': 'x', 'auth_level': 'dco'}))
    assert scope.taluka_value == DISTRICT_LEVEL
    assert scope.level == 'dco'


def test_scope_for_district_user_is_consolidated():
    scope = resolve_scope_from_request(
        _make_request({'auth_user': 'x', 'auth_level': 'district', 'auth_unit': 'Thane'})
    )
    assert scope.taluka_value == DISTRICT_LEVEL
    assert scope.district == 'Thane'


def test_scope_for_dco_staff_district_user_is_consolidated():
    scope = resolve_scope_from_request(
        _make_request({'auth_user': 'x', 'auth_level': 'district', 'auth_unit': quote('DCO Staff')})
    )
    assert scope.taluka_value == DISTRICT_LEVEL
    assert scope.district == 'DCO Staff'


def test_scope_for_taluka_user_is_their_own_unit():
    unit = 'Thane Taluka भिवंडी'
    scope = resolve_scope_from_request(
        _make_request({'auth_user': 'x', 'auth_level': 'taluka', 'auth_unit': quote(unit)})
    )
    assert scope.taluka_value == unit
    assert scope.district == 'Thane'


def test_scope_for_anonymous_is_consolidated():
    scope = resolve_scope_from_request(_make_request({}))
    assert scope == CONSOLIDATED_SCOPE


def test_default_scope_with_no_context_is_consolidated_never_unfiltered():
    from src.core.taluka.scope import current_scope

    assert current_scope() == CONSOLIDATED_SCOPE
    assert current_scope().taluka_value == DISTRICT_LEVEL


def test_scope_override_resets_after_context_exit():
    from src.core.taluka.scope import current_scope, DataScope

    other = DataScope(level='taluka', unit='Thane Taluka भिवंडी', district='Thane', taluka_value='Thane Taluka भिवंडी')
    with scope_override(other) as active:
        assert active is other
        assert current_scope() is other
    assert current_scope() == CONSOLIDATED_SCOPE


# ---------------------------------------------------------------------------
# Phase 2 — the 12-shape ORM read-isolation matrix.
#
# This is the contract for the entire feature (docs/plan.md Phase 2). It
# exercises the production `_inject_taluka_scope_filter` listener itself,
# bound to a throwaway in-memory SQLite sessionmaker, against two throwaway
# scoped models — no PostgreSQL required.
# ---------------------------------------------------------------------------
from src.core.taluka.models import TalukaScopedMixin
from src.core.taluka.orm_filter import _inject_taluka_scope_filter, TALUKA_SCOPE_ALL_OPTION
from src.core.taluka.scope import DataScope

_ScopeTestBase = declarative_base()


class _ScopeProbeContribution(TalukaScopedMixin, _ScopeTestBase):
    __tablename__ = 'scope_probe_contribution'
    id = Column(Integer, primary_key=True)
    district = Column(String(50), nullable=False)
    amount = Column(Integer, nullable=False, default=0)
    __table_args__ = (
        UniqueConstraint('district', 'taluka', name='uq_scope_probe_contribution'),
    )


class _ScopeProbeChild(TalukaScopedMixin, _ScopeTestBase):
    __tablename__ = 'scope_probe_child'
    id = Column(Integer, primary_key=True)
    contribution_id = Column(Integer, nullable=False)
    label = Column(String(50), nullable=False)


@pytest.fixture
def scoped_session():
    engine = create_engine('sqlite:///:memory:')
    TestSessionLocal = sessionmaker(bind=engine)
    event.listen(TestSessionLocal, 'do_orm_execute', _inject_taluka_scope_filter)
    _ScopeTestBase.metadata.create_all(engine)

    session = TestSessionLocal()
    a_consolidated = _ScopeProbeContribution(district='Thane', amount=100, taluka='')
    a_district_office = _ScopeProbeContribution(district='Thane', amount=40, taluka='__district_office__')
    a_taluka1 = _ScopeProbeContribution(district='Thane', amount=35, taluka='Thane Taluka Bhiwandi')
    a_taluka2 = _ScopeProbeContribution(district='Thane', amount=25, taluka='Thane Taluka Kalyan')
    session.add_all([a_consolidated, a_district_office, a_taluka1, a_taluka2])
    session.flush()
    session.add_all([
        _ScopeProbeChild(contribution_id=a_consolidated.id, label='c0', taluka=''),
        _ScopeProbeChild(contribution_id=a_district_office.id, label='c1', taluka='__district_office__'),
        _ScopeProbeChild(contribution_id=a_taluka1.id, label='c2', taluka='Thane Taluka Bhiwandi'),
        _ScopeProbeChild(contribution_id=a_taluka2.id, label='c3', taluka='Thane Taluka Kalyan'),
    ])
    session.commit()
    try:
        yield session
    finally:
        session.close()
        event.remove(TestSessionLocal, 'do_orm_execute', _inject_taluka_scope_filter)


def test_shape_01_query_model_scoped_to_consolidated(scoped_session):
    with scope_override(CONSOLIDATED_SCOPE):
        rows = scoped_session.query(_ScopeProbeContribution).all()
    assert [r.amount for r in rows] == [100]


def test_shape_02_query_single_column_scoped(scoped_session):
    with scope_override(CONSOLIDATED_SCOPE):
        amounts = scoped_session.query(_ScopeProbeContribution.amount).all()
    assert amounts == [(100,)]


def test_shape_03_query_func_sum_scoped(scoped_session):
    with scope_override(CONSOLIDATED_SCOPE):
        total = scoped_session.query(func.sum(_ScopeProbeContribution.amount)).scalar()
    assert total == 100


def test_shape_04_with_entities_count_scoped(scoped_session):
    with scope_override(CONSOLIDATED_SCOPE):
        count = (
            scoped_session.query(_ScopeProbeContribution)
            .with_entities(func.count(_ScopeProbeContribution.id))
            .scalar()
        )
    assert count == 1


def test_shape_05_group_by_scoped(scoped_session):
    taluka_scope = DataScope(
        level='taluka', unit='Thane Taluka Bhiwandi', district='Thane',
        taluka_value='Thane Taluka Bhiwandi',
    )
    with scope_override(taluka_scope):
        rows = (
            scoped_session.query(_ScopeProbeContribution.district, func.sum(_ScopeProbeContribution.amount))
            .group_by(_ScopeProbeContribution.district)
            .all()
        )
    assert rows == [('Thane', 35)]


def test_shape_06_select_20_style_scoped(scoped_session):
    with scope_override(CONSOLIDATED_SCOPE):
        result = scoped_session.execute(select(_ScopeProbeContribution)).scalars().all()
    assert [r.amount for r in result] == [100]


def test_shape_07_subquery_scoped(scoped_session):
    with scope_override(CONSOLIDATED_SCOPE):
        subq = select(_ScopeProbeContribution.id).where(_ScopeProbeContribution.amount >= 0).subquery()
        result = scoped_session.execute(select(func.count()).select_from(subq)).scalar()
    assert result == 1


def test_shape_08_multi_entity_join_scoped(scoped_session):
    with scope_override(CONSOLIDATED_SCOPE):
        rows = (
            scoped_session.query(_ScopeProbeContribution, _ScopeProbeChild)
            .join(_ScopeProbeChild, _ScopeProbeChild.contribution_id == _ScopeProbeContribution.id)
            .all()
        )
    assert len(rows) == 1
    a, b = rows[0]
    assert a.taluka == '' and b.taluka == ''


def test_shape_09_second_model_independently_isolated(scoped_session):
    with scope_override(CONSOLIDATED_SCOPE):
        rows = scoped_session.query(_ScopeProbeChild).all()
    assert [r.label for r in rows] == ['c0']


def test_shape_10_scope_all_execution_option_bypasses_filter(scoped_session):
    with scope_override(CONSOLIDATED_SCOPE):
        rows = (
            scoped_session.query(_ScopeProbeContribution)
            .execution_options(**{TALUKA_SCOPE_ALL_OPTION: True})
            .all()
        )
    assert len(rows) == 4


def test_shape_11_taluka_scope_sees_only_own_unit_never_consolidated(scoped_session):
    scope = DataScope(
        level='taluka', unit='Thane Taluka Kalyan', district='Thane',
        taluka_value='Thane Taluka Kalyan',
    )
    with scope_override(scope):
        rows = scoped_session.query(_ScopeProbeContribution).all()
        assert [r.amount for r in rows] == [25]
        # Even an explicit filter for the consolidated row cannot escape the
        # injected AND predicate — this is what stops a taluka user from
        # reading the district total by crafting their own query.
        assert scoped_session.query(_ScopeProbeContribution).filter(
            _ScopeProbeContribution.taluka == ''
        ).all() == []


def test_shape_12_cross_scope_queries_are_never_cross_cached(scoped_session):
    """The over-cached-lambda trap called out in docs/plan.md Phase 2.

    If the closure variable were baked into a cached compiled plan instead
    of re-read as a bound parameter, the second scope's query would return
    the first scope's rows.
    """
    with scope_override(CONSOLIDATED_SCOPE):
        consolidated_rows = scoped_session.query(_ScopeProbeContribution).all()

    taluka_scope = DataScope(
        level='taluka', unit='Thane Taluka Bhiwandi', district='Thane',
        taluka_value='Thane Taluka Bhiwandi',
    )
    with scope_override(taluka_scope):
        taluka_rows = scoped_session.query(_ScopeProbeContribution).all()

    assert [r.amount for r in consolidated_rows] == [100]
    assert [r.amount for r in taluka_rows] == [35]

    with scope_override(CONSOLIDATED_SCOPE):
        again = scoped_session.query(_ScopeProbeContribution).all()
    assert [r.amount for r in again] == [100]
