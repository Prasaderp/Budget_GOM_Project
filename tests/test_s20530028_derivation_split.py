import math
import random

import pytest

from src.schemes.s2053.subs.s20530028.derivation.split_policy import (
    PostRatioSplit,
    PreserveShareSplit,
    SPLIT_POLICY,
)


POLICY = PreserveShareSplit()


@pytest.mark.parametrize(
    ('arguments', 'expected'),
    [
        (('other', 30, 10, 1, 9, 0.2), 0.75),
        (('other', 0, 0, 1, 9, 0.6), 0.6),
        (('salary', 0, 0, 3, 1, None), 0.75),
        (('salary', 0, 0, 0, 0, None), 1.0),
    ],
)
def test_fallback_tiers_are_applied_in_order(arguments, expected):
    assert POLICY.filled_share(*arguments) == expected


def test_salary_tier_is_skipped_only_when_share_is_none():
    assert POLICY.filled_share('salary', 0, 0, 1, 3, None) == 0.25
    assert POLICY.filled_share('other', 0, 0, 1, 3, 0.0) == 0.0


@pytest.mark.parametrize(
    ('old_filled', 'old_vacant', 'expected'),
    [(20, -10, 1.0), (-10, 20, 0.0)],
)
def test_result_is_clamped_even_for_corrupt_legacy_values(old_filled, old_vacant, expected):
    assert POLICY.filled_share('salary', old_filled, old_vacant, 0, 0, None) == expected


@pytest.mark.parametrize('invalid', [math.nan, math.inf, 'broken'])
def test_non_finite_or_malformed_inputs_fall_through_safely(invalid):
    assert POLICY.filled_share('other', invalid, 0, 1, 3, invalid) == 0.25


def test_fresh_zero_post_cell_allocates_to_filled():
    assert POLICY.filled_share('other', 0, 0, 0, 0, None) == 1.0


def test_post_ratio_policy_uses_only_post_counts():
    policy = PostRatioSplit()
    assert policy.filled_share('other', 99, 1, 2, 6, 0.9) == 0.25
    assert policy.filled_share('other', 99, 1, 0, 0, 0.9) == 1.0


def test_default_policy_is_preserve_share():
    assert isinstance(SPLIT_POLICY, PreserveShareSplit)


def test_filled_plus_vacant_is_exact_across_adversarial_random_sweep():
    rng = random.Random(20530028)
    for _ in range(5000):
        total = rng.randint(0, 10**12)
        old_filled = rng.randint(0, 10**12)
        old_vacant = rng.randint(0, 10**12)
        filled_posts = rng.randint(0, 10**6)
        vacant_posts = rng.randint(0, 10**6)
        salary_share = rng.random() if rng.choice((True, False)) else None
        share = POLICY.filled_share(
            'other', old_filled, old_vacant, filled_posts, vacant_posts, salary_share
        )
        new_filled = int(round(total * share))
        new_vacant = total - new_filled
        assert 0 <= share <= 1
        assert new_filled + new_vacant == total
        assert new_filled >= 0 and new_vacant >= 0
