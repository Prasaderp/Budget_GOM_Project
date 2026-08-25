from types import SimpleNamespace

import pytest
from sqlalchemy import inspect

from src.schemes.s2053.subs.s20530028.config import (
    CLASS_1_2_KEY,
    CLASS_3_KEY,
    CLASS_4_KEY,
    DERIVED_POST_EXPENSES_FIELDS,
    DERIVED_POST_STATUS_FIELDS,
    POSITION_ORDER,
)
from src.schemes.s2053.subs.s20530028.derivation.mapping import (
    MEASURE_MAP,
    form_d_dearness_allowance,
    form_d_house_rent_allowance,
    pay_class_for,
    status_class_for,
)
from src.schemes.s2053.subs.s20530028.models import PostStatus


SEEDED_DESIGNATION_CASES = (
    ('Collector', CLASS_1_2_KEY, '1'),
    ('Additional Collector', CLASS_1_2_KEY, '1'),
    ('Deputy Collector', CLASS_1_2_KEY, '1'),
    ('Deputy Collector / Probationary Deputy Collector', CLASS_1_2_KEY, '1'),
    ('Tehsildar/Addl. Tehsildar/Chitnis (Secretary/Clerk)', CLASS_1_2_KEY, '1'),
    (
        'Tehsildar/Additional Tehsildar/Chitnis (Clerk/Secretary)/Probationary Tehsildar',
        CLASS_1_2_KEY,
        '1',
    ),
    ('Naib Tehsildar', CLASS_1_2_KEY, '2'),
    ('Naib Tehsildar/Probationary Naib Tehsildar', CLASS_1_2_KEY, '2'),
    ('Accounts Officer', CLASS_1_2_KEY, '2'),
    ('Asst. Accounts Officer', CLASS_1_2_KEY, '2'),
    ('Law Officer (Honorarium)', CLASS_1_2_KEY, '2'),
    ('Deputy Accountant', CLASS_3_KEY, '3'),
    ('Head Clerk/Deputy Accountant', CLASS_3_KEY, '3'),
    ('Head Clerk (Awwal Karkun)', CLASS_3_KEY, '3'),
    ('Divisional Officer', CLASS_3_KEY, '3'),
    ('Stenographer (Higher)', CLASS_3_KEY, '3'),
    ('Clerk', CLASS_3_KEY, '3'),
    ('Clerk/Land Surveyor/Recovery Clerk', CLASS_3_KEY, '3'),
    (
        'Stenographer (Lower)/Probationary Land Surveyor/Draftsman/Shirastedar',
        CLASS_3_KEY,
        '3',
    ),
    ('Vehicle Driver', CLASS_3_KEY, '3'),
    ('Telephone Operator/Steno-Typist(Law Officer Asst.)', CLASS_3_KEY, '3'),
    ('Peon/Naik/Havaldar/Watchman/Cleaner', CLASS_4_KEY, '4'),
)

PERMANENT_TEMPORARY_ALIAS_PAIRS = (
    ('Deputy Collector', 'Deputy Collector / Probationary Deputy Collector'),
    (
        'Tehsildar/Addl. Tehsildar/Chitnis (Secretary/Clerk)',
        'Tehsildar/Additional Tehsildar/Chitnis (Clerk/Secretary)/Probationary Tehsildar',
    ),
    ('Naib Tehsildar', 'Naib Tehsildar/Probationary Naib Tehsildar'),
    ('Head Clerk (Awwal Karkun)', 'Head Clerk/Deputy Accountant'),
)


@pytest.mark.parametrize(
    ('designation', 'class_type', 'expected_pay_class'),
    SEEDED_DESIGNATION_CASES,
)
def test_every_seeded_designation_has_the_expected_pay_class(
    designation, class_type, expected_pay_class
):
    assert tuple(case[0] for case in SEEDED_DESIGNATION_CASES) == tuple(POSITION_ORDER)
    assert pay_class_for(class_type, designation) == expected_pay_class


@pytest.mark.parametrize('permanent,temporary', PERMANENT_TEMPORARY_ALIAS_PAIRS)
def test_permanent_and_temporary_aliases_keep_the_same_pay_class(
    permanent, temporary
):
    assert pay_class_for(CLASS_1_2_KEY, permanent) == pay_class_for(
        CLASS_1_2_KEY, temporary
    )


def test_unknown_class_1_2_designation_defaults_to_class_2_with_warning(caplog):
    with caplog.at_level('WARNING'):
        assert pay_class_for(CLASS_1_2_KEY, 'Unexpected designation') == '2'
    assert 'Unexpected designation' in caplog.text


@pytest.mark.parametrize(
    ('class_type', 'pay_class'),
    [(CLASS_3_KEY, '3'), (CLASS_4_KEY, '4')],
)
def test_unambiguous_form_d_classes_ignore_designation(class_type, pay_class):
    assert pay_class_for(class_type, 'Unexpected designation') == pay_class


@pytest.mark.parametrize('class_type', ['', None, 'Class-5'])
def test_unknown_form_d_class_is_rejected(class_type):
    with pytest.raises(ValueError, match='class_type'):
        pay_class_for(class_type, 'Collector')


@pytest.mark.parametrize(
    ('pay_class', 'status_class'),
    [
        ('1', CLASS_1_2_KEY),
        ('2', CLASS_1_2_KEY),
        ('3', CLASS_3_KEY),
        ('4', CLASS_4_KEY),
    ],
)
def test_status_class_collapses_form_b_vocabulary(pay_class, status_class):
    assert status_class_for(pay_class) == status_class


def test_unknown_form_b_pay_class_is_rejected():
    with pytest.raises(ValueError, match='pay class'):
        status_class_for('5')


def test_measure_map_covers_exactly_form_c_money_columns():
    excluded = {
        'id',
        'scheme_code',
        'sub_scheme_code',
        'fiscal_year',
        'taluka',
        'district',
        'category',
        'class_type',
        'status',
        'posts',
    }
    model_money_columns = {
        column.key for column in inspect(PostStatus).columns if column.key not in excluded
    }
    assert {field for field, _ in MEASURE_MAP} == model_money_columns
    assert DERIVED_POST_STATUS_FIELDS == ('posts', *tuple(field for field, _ in MEASURE_MAP))
    assert DERIVED_POST_EXPENSES_FIELDS == ('vacant_posts',)


@pytest.mark.parametrize(
    ('basic_pay', 'grade_pay', 'hra_rate', 'da_rate'),
    [
        (0, 0, 'X', 0.64),
        (100, 25, 'X', 0.64),
        (101, 0, 'Y', 0.64),
        (10.5, 0, 'Z', 0.64),
        (99999.9, 12345, 'X', 0.53),
    ],
)
def test_value_adapters_match_form_d_template_arithmetic(
    basic_pay, grade_pay, hra_rate, da_rate
):
    row = SimpleNamespace(
        basic_pay=basic_pay,
        grade_pay=grade_pay,
        hra_rate=hra_rate,
    )
    assert form_d_dearness_allowance(row, da_rate) == round(
        (float(basic_pay) + float(grade_pay)) * da_rate
    )
    assert form_d_house_rent_allowance(row) == round(
        (float(basic_pay) + float(grade_pay))
        * {'X': 0.3, 'Y': 0.2, 'Z': 0.1}[hra_rate]
    )


def test_invalid_hra_rate_is_not_silently_replaced():
    row = SimpleNamespace(basic_pay=100, grade_pay=10, hra_rate='Q')
    with pytest.raises(KeyError):
        form_d_house_rent_allowance(row)
