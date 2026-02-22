from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Any, Tuple
import logging
from collections import defaultdict

from src.database import get_db
from src.core.templates import templates
from src.config import DCO_STAFF_IDENTIFIER
from src.utils_cache import ttl_cache
from src.utils_fiscal_year import get_fiscal_year_from_request
from .models import PostExpenses
from .helpers import get_no_cache_headers
from src.utils_auth import get_auth_level, get_auth_unit

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ui/s20530028/category-wise-info",
    tags=["UI - संवर्गनिहाय माहिती"],
    include_in_schema=False
)

@ttl_cache(ttl_seconds=300, max_size=20)
def get_category_data(db: Session, fiscal_year: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    class_mapping = {
        '1': 'वर्ग-1', '2': 'वर्ग-2', '3': 'वर्ग-3', '4': 'वर्ग-4'
    }
    class_order = ['वर्ग-1', 'वर्ग-2', 'वर्ग-3', 'वर्ग-4']

    aggregation_query = db.query(
        PostExpenses.class_type, PostExpenses.category,
        func.sum(PostExpenses.filled_posts).label("TotalFilled"),
        func.sum(PostExpenses.vacant_posts).label("TotalVacant")
    ).filter(
        PostExpenses.district != DCO_STAFF_IDENTIFIER,
        PostExpenses.fiscal_year == fiscal_year
    ).group_by(
        PostExpenses.class_type, PostExpenses.category
    ).all()

    summary_data: Dict[str, Dict[str, int]] = {cls_name: {} for cls_name in class_order}
    totals: Dict[str, Any] = defaultdict(int)

    for result in aggregation_query:
        class_key = class_mapping.get(getattr(result, 'class_type', None))
        if not class_key: continue

        filled = int(result.TotalFilled or 0)
        vacant = int(result.TotalVacant or 0)
        approved = filled + vacant

        if getattr(result, 'category', None) == 'Permanent':
            summary_data[class_key]['Filled_Perm'] = filled
            summary_data[class_key]['Vacant_Perm'] = vacant
            summary_data[class_key]['Approved_Perm'] = approved
            totals['Filled_Perm'] += filled
            totals['Vacant_Perm'] += vacant
            totals['Approved_Perm'] += approved
        elif getattr(result, 'category', None) == 'Temporary':
            summary_data[class_key]['Filled_Temp'] = filled
            summary_data[class_key]['Vacant_Temp'] = vacant
            summary_data[class_key]['Approved_Temp'] = approved
            totals['Filled_Temp'] += filled
            totals['Vacant_Temp'] += vacant
            totals['Approved_Temp'] += approved

    table_rows = []
    for i, class_name in enumerate(class_order, 1):
        row_data = summary_data.get(class_name, {})
        table_rows.append({
            "Sr No.": i,
            "Cadre": class_name,
            "Approved - Permanent": row_data.get("Approved_Perm", 0),
            "Approved - Temporary": row_data.get("Approved_Temp", 0),
            "Filled - Permanent": row_data.get("Filled_Perm", 0),
            "Filled - Temporary": row_data.get("Filled_Temp", 0),
            "Vacant - Permanent": row_data.get("Vacant_Perm", 0),
            "Vacant - Temporary": row_data.get("Vacant_Temp", 0)
        })

    totals['Sr No.'] = "--"
    totals['Cadre'] = "एकूण"
    totals_renamed = {
        "Sr No.": totals['Sr No.'], "Cadre": totals['Cadre'],
        "Approved - Permanent": totals['Approved_Perm'], "Approved - Temporary": totals['Approved_Temp'],
        "Filled - Permanent": totals['Filled_Perm'], "Filled - Temporary": totals['Filled_Temp'],
        "Vacant - Permanent": totals['Vacant_Perm'], "Vacant - Temporary": totals['Vacant_Temp']
    }

    return table_rows, totals_renamed


@router.get("", response_class=HTMLResponse)
async def ui_category_wise_info(request: Request, db: Session = Depends(get_db)):
    auth_level = get_auth_level(request)
    auth_unit = get_auth_unit(request)

    if auth_level == 'district' and auth_unit == DCO_STAFF_IDENTIFIER:
        raise HTTPException(status_code=403, detail="Access denied")
    if auth_level in ('district', 'taluka'):
        raise HTTPException(status_code=403, detail="Access denied")

    fiscal_year = get_fiscal_year_from_request(request, db)
    table_rows, totals = get_category_data(db, fiscal_year)

    response = templates.TemplateResponse("schemes/s2053/subs/s20530028/category_wise_info.html", {
        "request": request, "resource_name": "संवर्गनिहाय माहिती",
        "table_rows": table_rows, "totals": totals, "auth_level": auth_level
    })
    response.headers.update(get_no_cache_headers())
    return response
