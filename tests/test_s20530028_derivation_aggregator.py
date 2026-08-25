from decimal import Decimal

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from src.core.taluka.constants import DISTRICT_OFFICE
from src.core.taluka.orm_filter import _inject_taluka_scope_filter
from src.database import Base
from src.schemes.s2053.subs.s20530028.config import (
    CLASS_1_2_KEY,
    CLASS_3_KEY,
    CLASS_4_KEY,
)
from src.schemes.s2053.subs.s20530028.derivation.aggregator import (
    CellTotals,
    aggregate_pay_classes,
    roll_up_to_status_classes,
)
from src.schemes.s2053.subs.s20530028.derivation.mapping import (
    form_d_dearness_allowance,
    form_d_house_rent_allowance,
)
from src.schemes.s2053.subs.s20530028.models import BudgetPostDetails


@pytest.fixture
def db():
    engine = create_engine('sqlite:///:memory:')
    session_factory = sessionmaker(bind=engine)
    event.listen(session_factory, 'do_orm_execute', _inject_taluka_scope_filter)
    Base.metadata.create_all(engine, tables=[BudgetPostDetails.__table__])
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        event.remove(session_factory, 'do_orm_execute', _inject_taluka_scope_filter)
        engine.dispose()


def _row(db, designation, class_type, *, category='Permanent', **values):
    defaults = dict(
        scheme_code='2053',
        sub_scheme_code='20530028',
        fiscal_year='2025-26',
        district='Mumbai City',
        taluka=DISTRICT_OFFICE,
        category=category,
        sanctioned_posts_prev1=0,
        sanctioned_posts_curr=0,
        special_pay=0,
        basic_pay=0,
        grade_pay=0,
        local_supplementary_allowance=0,
        vehicle_allowance=0,
        washing_allowance=0,
        cash_allowance=0,
        footwear_allowance_other=0,
        hra_rate='X',
    )
    defaults.update(values)
    row = BudgetPostDetails(
        designation=designation,
        class_type=class_type,
        **defaults,
    )
    db.add(row)
    return row


def _seed_mumbai_cells(db):
    # Non-zero rows copied from DATAINSERTION_20530028.sql, Mumbai City/Permanent.
    _row(db, 'Collector', CLASS_1_2_KEY, sanctioned_posts_curr=1, basic_pay=2442,
         local_supplementary_allowance=4)
    _row(db, 'Deputy Collector', CLASS_1_2_KEY, sanctioned_posts_curr=1, basic_pay=1253,
         local_supplementary_allowance=4, vehicle_allowance=65)
    _row(db, 'Tehsildar/Addl. Tehsildar/Chitnis (Secretary/Clerk)', CLASS_1_2_KEY,
         sanctioned_posts_curr=1, basic_pay=768, local_supplementary_allowance=3,
         vehicle_allowance=65)
    _row(db, 'Stenographer (Higher)', CLASS_3_KEY, sanctioned_posts_curr=1, basic_pay=758,
         local_supplementary_allowance=3, vehicle_allowance=32)
    _row(db, 'Head Clerk (Awwal Karkun)', CLASS_3_KEY, sanctioned_posts_curr=2, basic_pay=867,
         local_supplementary_allowance=8, vehicle_allowance=65, washing_allowance=17)
    _row(db, 'Clerk', CLASS_3_KEY, sanctioned_posts_curr=23, basic_pay=6637,
         local_supplementary_allowance=55, vehicle_allowance=439)
    _row(db, 'Peon/Naik/Havaldar/Watchman/Cleaner', CLASS_4_KEY,
         sanctioned_posts_curr=32, basic_pay=8953, local_supplementary_allowance=49,
         vehicle_allowance=552, washing_allowance=96)

    for designation, count in (
        ('Additional Collector', 1),
        ('Deputy Collector / Probationary Deputy Collector', 1),
        ('Tehsildar/Additional Tehsildar/Chitnis (Clerk/Secretary)/Probationary Tehsildar', 2),
        ('Accounts Officer', 2),
        ('Asst. Accounts Officer', 1),
        ('Law Officer (Honorarium)', 1),
    ):
        _row(db, designation, CLASS_1_2_KEY, category='Temporary', sanctioned_posts_curr=count)
    db.flush()


def test_aggregates_real_seed_cells_and_form_d_computed_measures(db):
    _seed_mumbai_cells(db)
    totals = aggregate_pay_classes(
        db,
        taluka=DISTRICT_OFFICE,
        district='Mumbai City',
        fiscal_year='2025-26',
        category='Permanent',
        da_rate=0.64,
    )
    status = roll_up_to_status_classes(totals)

    assert status[CLASS_1_2_KEY].sanctioned == 3
    assert status[CLASS_1_2_KEY].salary == 4463
    assert status[CLASS_1_2_KEY].local_supplementary_allowance == 11
    assert status[CLASS_1_2_KEY].travel_allowance == 130
    assert status[CLASS_3_KEY].sanctioned == 26
    assert status[CLASS_3_KEY].salary == 8262
    assert status[CLASS_3_KEY].other == 17
    assert status[CLASS_4_KEY].sanctioned == 32
    assert status[CLASS_4_KEY].salary == 8953
    assert status[CLASS_4_KEY].other == 96

    source_rows = db.query(BudgetPostDetails).execution_options(taluka_scope_all=True).filter(
        BudgetPostDetails.category == 'Permanent'
    ).all()
    assert sum(cell.dearness_allowance for cell in totals.values()) == sum(
        form_d_dearness_allowance(row, 0.64) for row in source_rows
    )
    assert sum(cell.house_rent_allowance for cell in totals.values()) == sum(
        form_d_house_rent_allowance(row) for row in source_rows
    )


def test_temporary_class_1_and_2_designations_remain_separate_pay_classes(db):
    _seed_mumbai_cells(db)
    totals = aggregate_pay_classes(
        db, taluka=DISTRICT_OFFICE, district='Mumbai City', fiscal_year='2025-26',
        category='Temporary', da_rate=0.64
    )
    assert totals['1'].sanctioned == 4
    assert totals['2'].sanctioned == 4


def test_query_bypasses_ambient_scope_but_reads_only_requested_contribution(db):
    _row(db, 'Collector', CLASS_1_2_KEY, district='Thane', taluka=DISTRICT_OFFICE,
         sanctioned_posts_curr=2)
    _row(db, 'Collector', CLASS_1_2_KEY, district='Thane', taluka='Thane Taluka',
         sanctioned_posts_curr=7)
    db.flush()

    def aggregate(taluka):
        return aggregate_pay_classes(
            db, taluka=taluka, district='Thane', fiscal_year='2025-26',
            category='Permanent', da_rate=0.64
        )['1'].sanctioned

    assert aggregate(DISTRICT_OFFICE) == 2
    assert aggregate('Thane Taluka') == 7


def test_aggregator_uses_one_select_and_quantises_salary_once_per_cell(db):
    _row(db, 'Collector', CLASS_1_2_KEY, basic_pay=Decimal('0.6'))
    _row(db, 'Additional Collector', CLASS_1_2_KEY, basic_pay=Decimal('0.6'))
    db.flush()
    selects = []

    def count_selects(_conn, _cursor, statement, _parameters, _context, _executemany):
        if statement.lstrip().upper().startswith('SELECT'):
            selects.append(statement)

    event.listen(db.bind, 'before_cursor_execute', count_selects)
    try:
        totals = aggregate_pay_classes(
            db, taluka=DISTRICT_OFFICE, district='Mumbai City', fiscal_year='2025-26',
            category='Permanent', da_rate=0.64
        )
    finally:
        event.remove(db.bind, 'before_cursor_execute', count_selects)

    assert len(selects) == 1
    assert totals['1'].salary == 1


def test_unknown_class_is_skipped_without_losing_valid_rows(db, caplog):
    _row(db, 'Collector', CLASS_1_2_KEY, sanctioned_posts_curr=2)
    _row(db, 'Malformed seed row', 'Class-5', sanctioned_posts_curr=99)
    db.flush()
    with caplog.at_level('WARNING'):
        totals = aggregate_pay_classes(
            db, taluka=DISTRICT_OFFICE, district='Mumbai City', fiscal_year='2025-26',
            category='Permanent', da_rate=0.64
        )
    assert totals['1'].sanctioned == 2
    assert sum(cell.sanctioned for cell in totals.values()) == 2
    assert 'Class-5' in caplog.text


def test_roll_up_is_measure_wise_and_tolerates_missing_zero_pay_classes():
    rolled = roll_up_to_status_classes({
        '1': CellTotals(sanctioned=2, salary=10, other=3),
        '2': CellTotals(sanctioned=4, salary=20, other=5),
        '4': CellTotals(sanctioned=7, salary=30, other=9),
    })
    assert rolled[CLASS_1_2_KEY] == CellTotals(sanctioned=6, salary=30, other=8)
    assert rolled[CLASS_3_KEY] == CellTotals()
    assert rolled[CLASS_4_KEY] == CellTotals(sanctioned=7, salary=30, other=9)
