"""Read-only per-taluka breakdown page (docs/plan.md Phase 12).

Shows, for a chosen form/table and natural key, the district-office
contribution row, each active taluka's contribution row, and the
consolidated total -- the one place a district or DCO user can see the
taluka-level split that every other view in the system deliberately hides
behind the consolidated row (docs/plan.md §5.3 point 4, §6 Phase 12).

A taluka user is denied outright: read-only access to siblings would
contradict the isolation guarantee the whole feature is built on
(docs/plan.md §2.3).
"""
import logging
from typing import Any, Dict, List, Optional, Tuple, Type

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from src.config import DCO_STAFF_IDENTIFIER, REGULAR_DISTRICTS, DISTRICTS_MR
from src.core.registry import scheme_registry
from src.core.taluka.constants import DISTRICT_LEVEL, DISTRICT_OFFICE, DISTRICT_OFFICE_LABEL_MR
from src.core.taluka.consolidation import _active_taluka_values, _column_classes
from src.core.taluka.models import iter_scoped_models, natural_key_columns
from src.core.taluka.orm_filter import TALUKA_SCOPE_ALL_OPTION
from src.core.templates import render
from src.database import get_db
from src.utils_auth import is_authenticated, get_auth_level, get_auth_unit
from src.utils_fiscal_year import get_fiscal_year_from_request
from src.utils_scheme import get_scheme_base_template

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ui/s{scheme_code}/taluka-breakdown",
    tags=["UI - तालुका विभागणी"],
    include_in_schema=False,
)

_MAX_PAGE_SIZE = 500
_scoped_tables_by_name: Dict[str, Type] = {}


def _scoped_model_for_table(table_name: str) -> Optional[Type]:
    if not _scoped_tables_by_name:
        _scoped_tables_by_name.update({m.__tablename__: m for m in iter_scoped_models()})
    return _scoped_tables_by_name.get(table_name)


def _contributor_label(taluka_value: str) -> str:
    if taluka_value == DISTRICT_OFFICE:
        return DISTRICT_OFFICE_LABEL_MR
    if " Taluka " in taluka_value:
        return taluka_value.split(" Taluka ", 1)[1]
    return taluka_value


@router.get("", response_class=HTMLResponse)
async def ui_taluka_breakdown(
    request: Request,
    scheme_code: str,
    db: Session = Depends(get_db),
    form: Optional[str] = Query(None),
    district: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=_MAX_PAGE_SIZE),
):
    if not is_authenticated(request):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    level = get_auth_level(request)
    unit = get_auth_unit(request)

    if level == "taluka":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Taluka users cannot view the breakdown page")
    if level not in ("district", "dco"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    if level == "district":
        if not unit or unit == DCO_STAFF_IDENTIFIER:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="DCO Staff has no taluka breakdown")
        target_district = unit
    else:
        target_district = district or REGULAR_DISTRICTS[0]
        if target_district not in REGULAR_DISTRICTS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid district selection")

    config = scheme_registry.get_scheme(scheme_code)
    if not config or not config.implemented:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sub-scheme not available")

    form_options: List[Tuple[str, str]] = [
        (name, cfg.table_name)
        for name, cfg in config.forms.items()
        if cfg.table_name and _scoped_model_for_table(cfg.table_name) is not None
    ]
    if not form_options:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This sub-scheme has no taluka-scoped data")

    table_by_form = dict(form_options)
    selected_form = form if form in table_by_form else form_options[0][0]
    model = _scoped_model_for_table(table_by_form[selected_form])

    fiscal_year = get_fiscal_year_from_request(request, db)

    active_talukas = _active_taluka_values(db, target_district)
    contributor_values = [DISTRICT_OFFICE] + active_talukas

    key_cols = natural_key_columns(model)
    additive_fields = [name for name, cls in _column_classes(model).items() if cls == "additive"]

    all_rows = (
        db.query(model)
        .execution_options(**{TALUKA_SCOPE_ALL_OPTION: True})
        .filter(model.district == target_district, model.fiscal_year == fiscal_year)
        .all()
    )

    groups: Dict[tuple, Dict[str, Any]] = {}
    for row in all_rows:
        key = tuple(getattr(row, c) for c in key_cols)
        groups.setdefault(key, {})[row.taluka] = row

    sorted_keys = sorted(groups.keys(), key=lambda k: tuple(str(v) for v in k))
    total_groups = len(sorted_keys)
    start = (page - 1) * page_size
    page_keys = sorted_keys[start:start + page_size]

    display_groups = []
    for key in page_keys:
        rows_by_taluka = groups[key]
        contributors = [
            {
                "label": _contributor_label(tv),
                "values": {f: (getattr(rows_by_taluka.get(tv), f, 0) or 0) for f in additive_fields},
            }
            for tv in contributor_values
        ]
        consolidated_row = rows_by_taluka.get(DISTRICT_LEVEL)
        display_groups.append({
            "key_labels": list(zip(key_cols, key)),
            "contributors": contributors,
            "total": {f: (getattr(consolidated_row, f, 0) or 0) for f in additive_fields},
        })

    template_data = {
        "request": request,
        "resource_name": "तालुका विभागणी",
        "scheme_code": scheme_code,
        "district": target_district,
        "district_label": DISTRICTS_MR.get(target_district, target_district),
        "fiscal_year": fiscal_year,
        "form_options": form_options,
        "selected_form": selected_form,
        "field_names": additive_fields,
        "groups": display_groups,
        "page": page,
        "page_size": page_size,
        "total_groups": total_groups,
        "has_active_talukas": bool(active_talukas),
        "auth_level": level,
        "districts": REGULAR_DISTRICTS,
        "district_names": DISTRICTS_MR,
        "base_template": get_scheme_base_template(request),
    }
    return render(request, "taluka_breakdown.html", template_data)
