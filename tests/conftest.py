"""Shared fixtures for the taluka consolidation regression suite (docs/plan.md
Phase 13). Each existing Phase's test file (test_taluka_scope.py,
test_taluka_consolidation.py, test_taluka_chatbot.py) keeps its own local
fixtures unmodified -- they were each independently verified against a
specific phase's contract. This module exists only for tests written after
Phase 13 that need the three canonical regression scenarios without
re-deriving the auth-cookie/session boilerplate: a district with active
talukas, a district with none (Mumbai City), and DCO Staff.
"""

from contextlib import contextmanager
from urllib.parse import quote

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from starlette.requests import Request

from src import models
from src.core.taluka.orm_filter import _inject_taluka_scope_filter
from src.database import Base

# Mumbai City carries zero possible talukas in the production mapping
# (src/utils_taluka.py) -- the canonical "this district behaves exactly as
# before the feature" fixture, regression matrix item (a).
MUMBAI_CITY = "Mumbai City"

# Thane carries 8 possible talukas -- used as the canonical "district with
# active talukas" fixture.
THANE = "Thane"
THANE_TALUKAS = ["Thane Taluka भिवंडी", "Thane Taluka कल्याण"]


def make_cookie_request(cookies: dict, path: str = "/", method: str = "GET") -> Request:
    cookie_header = "; ".join(f"{k}={v}" for k, v in cookies.items()).encode()
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "headers": [(b"cookie", cookie_header)] if cookies else [],
        "query_string": b"",
    }
    return Request(scope)


def district_request(district: str, path: str = "/", method: str = "GET") -> Request:
    return make_cookie_request(
        {
            "auth_user": "x",
            "auth_role": "assistant",
            "auth_level": "district",
            "auth_unit": quote(district),
        },
        path,
        method,
    )


def district_write_request(district: str, path: str = "/") -> Request:
    return district_request(district, path, "POST")


def taluka_request(unit: str, path: str = "/") -> Request:
    return make_cookie_request(
        {
            "auth_user": "x",
            "auth_role": "assistant",
            "auth_level": "taluka",
            "auth_unit": quote(unit),
        },
        path,
    )


def officer_request(district: str, path: str = "/") -> Request:
    return make_cookie_request(
        {
            "auth_user": "x",
            "auth_role": "officer1",
            "auth_level": "district",
            "auth_unit": quote(district),
        },
        path,
    )


def dco_request(path: str = "/") -> Request:
    return make_cookie_request(
        {"auth_user": "x", "auth_role": "dco", "auth_level": "dco", "auth_unit": ""},
        path,
    )


def dco_write_request(path: str = "/") -> Request:
    """dco_asst (role='assistant') -- the only level='dco' account HTTP handlers
    let past the role gate; see src/routers/auth.py:216-219. `unit` is a
    division, matching production (`_writable_taluka_value()` must never
    derive the district from it)."""
    return make_cookie_request(
        {
            "auth_user": "x",
            "auth_role": "assistant",
            "auth_level": "dco",
            "auth_unit": quote("KONKAN DIVISION"),
        },
        path,
        "POST",
    )


def dco_staff_request(path: str = "/") -> Request:
    from src.config import DCO_STAFF_IDENTIFIER

    return district_request(DCO_STAFF_IDENTIFIER, path)


@pytest.fixture
def scoped_session_factory():
    """Yields a factory `make_session(*extra_tables)` producing an in-memory
    SQLite session bound to the production `_inject_taluka_scope_filter`
    listener plus `TalukaUserManagement` / `DistrictTalukaSelection`, so any
    scoped model's table can be added per-test without duplicating the engine
    / listener wiring (docs/plan.md Phase 13, "shared fixtures").
    """
    opened = []

    @contextmanager
    def _make(*extra_tables):
        engine = create_engine("sqlite:///:memory:")
        TestSessionLocal = sessionmaker(bind=engine)
        event.listen(TestSessionLocal, "do_orm_execute", _inject_taluka_scope_filter)
        Base.metadata.create_all(
            engine,
            tables=[
                models.TalukaUserManagement.__table__,
                models.DistrictTalukaSelection.__table__,
                *extra_tables,
            ],
        )
        session = TestSessionLocal()
        try:
            yield session
        finally:
            session.close()
            event.remove(
                TestSessionLocal, "do_orm_execute", _inject_taluka_scope_filter
            )

    return _make


def activate_talukas(db, district: str, talukas: list) -> None:
    db.add(models.DistrictTalukaSelection(district=district, selected_talukas=talukas))
    for t in talukas:
        db.add(
            models.TalukaUserManagement(
                district=district, taluka_name=t, is_active=True
            )
        )
    db.flush()
