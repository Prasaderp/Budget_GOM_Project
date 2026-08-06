"""Request-scoped data scope: the one contextvar the ORM read filter reads.

DataScope.taluka_value is the only field the Phase 2 read filter consults.
The other fields (level, unit, district) are carried for write-redirection
and ACL callers that need the raw auth context — they must never be used to
derive a *different* read filter than taluka_value encodes, or the "default
is always consolidated" safety property in docs/plan.md section 2.3 breaks.
"""
from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import Iterator, Optional

from fastapi import Request

from src.core.taluka.constants import DISTRICT_LEVEL
from src.utils_auth import get_auth_level, get_auth_unit


@dataclass(frozen=True)
class DataScope:
    level: str
    unit: str
    district: Optional[str]
    taluka_value: str


# The fail-safe default: no request context, an unauthenticated caller, a
# background thread that never set a scope — all of them read consolidated
# rows, identical to pre-feature behaviour. Never "unfiltered".
CONSOLIDATED_SCOPE = DataScope(level='', unit='', district=None, taluka_value=DISTRICT_LEVEL)

_scope_var: ContextVar[DataScope] = ContextVar('taluka_data_scope', default=CONSOLIDATED_SCOPE)


def resolve_scope_from_request(request: Request) -> DataScope:
    """Derive the caller's DataScope from auth cookies.

    Only a taluka-level unit resolves to a non-consolidated taluka_value.
    District assistants, district officers, DCO, DCO Staff and anonymous
    callers all read taluka_value == '' (consolidated) — they reach their
    own contribution row only through resolve_editable_row()'s explicit
    opt-in bypass (Phase 6), never through this default read scope.
    """
    # Deferred: src.utils_district transitively imports src.config, which
    # imports the scheme package tree, which imports src.utils_district back
    # — a module-level import here is the first thing to observe that cycle
    # mid-initialization whenever src.core.taluka is imported before
    # src.config has been loaded by anything else.
    from src.utils_district import get_district_from_taluka

    level = get_auth_level(request)
    unit = get_auth_unit(request)

    if level == 'taluka' and unit:
        district = get_district_from_taluka(unit)
        if district:
            return DataScope(level=level, unit=unit, district=district, taluka_value=unit)
        return DataScope(level=level, unit=unit, district=None, taluka_value=DISTRICT_LEVEL)

    if level == 'district' and unit:
        return DataScope(level=level, unit=unit, district=unit, taluka_value=DISTRICT_LEVEL)

    if level == 'dco':
        return DataScope(level=level, unit=unit, district=None, taluka_value=DISTRICT_LEVEL)

    return CONSOLIDATED_SCOPE


def current_scope() -> DataScope:
    return _scope_var.get()


def set_scope(scope: DataScope) -> Token:
    return _scope_var.set(scope)


def reset_scope(token: Token) -> None:
    _scope_var.reset(token)


@contextmanager
def scope_override(scope: DataScope) -> Iterator[DataScope]:
    """Temporarily install `scope` as the current scope.

    For services (consolidation, provisioning) and tests that need a known
    scope without going through a Request — not for use in request handlers,
    which get their scope from TalukaScopeMiddleware (Phase 2).
    """
    token = _scope_var.set(scope)
    try:
        yield scope
    finally:
        _scope_var.reset(token)
