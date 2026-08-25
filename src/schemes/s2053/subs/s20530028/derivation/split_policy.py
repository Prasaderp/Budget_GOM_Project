"""Policies for allocating Form D totals across Form C Filled/Vacant rows."""

from math import isfinite
from typing import Protocol


class SplitPolicy(Protocol):
    def filled_share(
        self,
        measure: str,
        old_filled: int | float,
        old_vacant: int | float,
        filled_posts: int,
        vacant_posts: int,
        salary_share: float | None,
    ) -> float: ...


def _share(filled, vacant) -> float | None:
    try:
        filled, vacant = float(filled), float(vacant)
    except (TypeError, ValueError, OverflowError):
        return None
    denominator = filled + vacant
    if not isfinite(filled) or not isfinite(denominator) or denominator <= 0:
        return None
    return min(1.0, max(0.0, filled / denominator))


def _bounded(value) -> float | None:
    try:
        value = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return min(1.0, max(0.0, value)) if isfinite(value) else None


class PreserveShareSplit:
    """Preserve an existing measure share, with evidence-based fallbacks."""

    def filled_share(
        self,
        measure: str,
        old_filled: int | float,
        old_vacant: int | float,
        filled_posts: int,
        vacant_posts: int,
        salary_share: float | None,
    ) -> float:
        del measure
        old_share = _share(old_filled, old_vacant)
        if old_share is not None:
            return old_share
        if salary_share is not None:
            salary_fallback = _bounded(salary_share)
            if salary_fallback is not None:
                return salary_fallback
        post_share = _share(filled_posts, vacant_posts)
        return post_share if post_share is not None else 1.0


class PostRatioSplit:
    """Allocate every measure using the Filled/Vacant post ratio."""

    def filled_share(
        self,
        measure: str,
        old_filled: int | float,
        old_vacant: int | float,
        filled_posts: int,
        vacant_posts: int,
        salary_share: float | None,
    ) -> float:
        del measure, old_filled, old_vacant, salary_share
        post_share = _share(filled_posts, vacant_posts)
        return post_share if post_share is not None else 1.0


SPLIT_POLICY: SplitPolicy = PreserveShareSplit()
