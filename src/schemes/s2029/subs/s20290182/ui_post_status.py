"""UI routes for post status (Form C) - sub-scheme 20290182"""
from fastapi import APIRouter, Depends, Request, Form, HTTPException, status, Query
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, Dict, Any
from urllib.parse import urlencode
from collections import defaultdict
import json
import logging
import pandas as pd
import io

from src.database import get_db
from src.core.templates import templates
from src.config import DISTRICTS, REGULAR_DISTRICTS, DCO_STAFF_IDENTIFIER, DISTRICTS_MR
from src.utils_taluka import is_taluka_allowed, get_district_from_taluka_name
from src.utils_district import build_district_filter, get_district_from_taluka
from src.utils_fiscal_year import get_fiscal_year_from_request, get_relative_fiscal_years
from src.utils_scheme import get_scheme_from_cookies
from src.utils_cache import ttl_cache
from src.utils_timing import check_data_filling_allowed
from .excel_export import export_original_workbook_async
from src.utils_fiscal_year import get_fiscal_year_from_request as get_fy
from src.audit_service import AuditService
from .models import PostStatus
from .config import (
    SCHEME_CONFIG, CATEGORIES, CLASSES_SHEET1_2, STATUSES,
    CATEGORIES_MR, CLASSES_MR, STATUSES_MR,
    CLASS_1_2_KEY, CLASS_3_KEY, CLASS_4_KEY, VALID_CLASS_KEYS,
    CLASS_MAPPING, METRICS_DB_KEYS, METRICS_LABELS
)
from .helpers import (
    check_edit_permission_for_scheme, validate_access_control,
    validate_numeric_inputs, get_no_cache_headers
)
from src.utils_auth import get_auth_unit

templates.env.globals['zip'] = zip

router = APIRouter(
    prefix="/ui/s20290182/post-status",
    tags=["UI - प्रपत्र क"],
    include_in_schema=False
)

logger = logging.getLogger(__name__)

CLASS_MR_MAP = {
    CLASS_1_2_KEY: 'वर्ग-1 व 2',
    CLASS_3_KEY: 'वर्ग-3',
    CLASS_4_KEY: 'वर्ग-4'
}

def _process_summary_data(summary: Dict, fiscal_year: str, district: Optional[str] = None) -> Dict[str, Any]:
    """Process summary data into metric rows and totals"""
    permanent_metric_rows = []
    temporary_metric_rows = []
    comparison_metrics_keys = []
    perm_category_totals = defaultdict(int)
    temp_category_totals = defaultdict(int)
    
    cost_fields = ['Salary', 'GradePay', 'SpecialPay', 'DearnessAllowance', 'LocalSupplemetoryAllowance', 'HouseRentAllowance', 'TravelAllowance', 'Other']
    
    for label in METRICS_LABELS:
        perm_row = {'Label': label}
        temp_row = {'Label': label}
        metric_key_for_comp = None
        
        for class_key in VALID_CLASS_KEYS + ['एकूण']:
            is_total_col = (class_key == 'एकूण')
            perm_filled_data = defaultdict(int)
            perm_vacant_data = defaultdict(int)
            temp_filled_data = defaultdict(int)
            temp_vacant_data = defaultdict(int)
            
            if not is_total_col:
                perm_filled_data = summary['Permanent'].get(CLASS_MR_MAP.get(class_key, class_key), {}).get('Filled', defaultdict(int))
                perm_vacant_data = summary['Permanent'].get(CLASS_MR_MAP.get(class_key, class_key), {}).get('Vacant', defaultdict(int))
                temp_filled_data = summary['Temporary'].get(CLASS_MR_MAP.get(class_key, class_key), {}).get('Filled', defaultdict(int))
                temp_vacant_data = summary['Temporary'].get(CLASS_MR_MAP.get(class_key, class_key), {}).get('Vacant', defaultdict(int))
            else:
                for ck in VALID_CLASS_KEYS:
                    ck_mr = CLASS_MR_MAP.get(ck, ck)
                    perm_filled_class_data = summary['Permanent'].get(ck_mr, {}).get('Filled', defaultdict(int))
                    perm_vacant_class_data = summary['Permanent'].get(ck_mr, {}).get('Vacant', defaultdict(int))
                    temp_filled_class_data = summary['Temporary'].get(ck_mr, {}).get('Filled', defaultdict(int))
                    temp_vacant_class_data = summary['Temporary'].get(ck_mr, {}).get('Vacant', defaultdict(int))
                    
                    for dbk in METRICS_DB_KEYS:
                        perm_filled_data[dbk] += perm_filled_class_data.get(dbk, 0)
                        perm_vacant_data[dbk] += perm_vacant_class_data.get(dbk, 0)
                        temp_filled_data[dbk] += temp_filled_class_data.get(dbk, 0)
                        temp_vacant_data[dbk] += temp_vacant_class_data.get(dbk, 0)
                    
                    for field in ['Posts', 'Salary', 'GradePay', 'SpecialPay', 'DearnessAllowance', 'LocalSupplemetoryAllowance', 'HouseRentAllowance', 'TravelAllowance', 'Other']:
                        perm_filled_data[field] += perm_filled_class_data.get(field, 0)
                        perm_vacant_data[field] += perm_vacant_class_data.get(field, 0)
                        temp_filled_data[field] += temp_filled_class_data.get(field, 0)
                        temp_vacant_data[field] += temp_vacant_class_data.get(field, 0)
            
            val_perm_filled = val_perm_vacant = val_temp_filled = val_temp_vacant = 0
            
            if label == 'पदे':
                metric_key_for_comp = 'पदे'
                val_perm_filled = perm_filled_data.get('Posts', 0)
                val_perm_vacant = perm_vacant_data.get('Posts', 0)
                val_temp_filled = temp_filled_data.get('Posts', 0)
                val_temp_vacant = temp_vacant_data.get('Posts', 0)
            elif label == 'वेतन':
                metric_key_for_comp = 'वेतन'
                val_perm_filled = perm_filled_data.get('Salary', 0)
                val_temp_filled = temp_filled_data.get('Salary', 0)
                val_perm_vacant = perm_vacant_data.get('Salary', 0)
                val_temp_vacant = temp_vacant_data.get('Salary', 0)
            elif label == 'ग्रेड पे':
                metric_key_for_comp = 'ग्रेड पे'
                val_perm_filled = perm_filled_data.get('GradePay', 0)
                val_temp_filled = temp_filled_data.get('GradePay', 0)
                val_perm_vacant = perm_vacant_data.get('GradePay', 0)
                val_temp_vacant = temp_vacant_data.get('GradePay', 0)
            elif label == 'विशेष वेतन':
                metric_key_for_comp = 'विशेष वेतन'
                val_perm_filled = perm_filled_data.get('SpecialPay', 0)
                val_temp_filled = temp_filled_data.get('SpecialPay', 0)
                val_perm_vacant = perm_vacant_data.get('SpecialPay', 0)
                val_temp_vacant = temp_vacant_data.get('SpecialPay', 0)
            elif label == 'एकूण वेतन':
                metric_key_for_comp = 'एकूण वेतन'
                val_perm_filled = perm_filled_data.get('Salary', 0) + perm_filled_data.get('GradePay', 0) + perm_filled_data.get('SpecialPay', 0)
                val_temp_filled = temp_filled_data.get('Salary', 0) + temp_filled_data.get('GradePay', 0) + temp_filled_data.get('SpecialPay', 0)
                val_perm_vacant = perm_vacant_data.get('Salary', 0) + perm_vacant_data.get('GradePay', 0) + perm_vacant_data.get('SpecialPay', 0)
                val_temp_vacant = temp_vacant_data.get('Salary', 0) + temp_vacant_data.get('GradePay', 0) + temp_vacant_data.get('SpecialPay', 0)
            elif label == 'महा.भत्ता':
                metric_key_for_comp = 'महा.भत्ता'
                val_perm_filled = perm_filled_data.get('DearnessAllowance', 0)
                val_temp_filled = temp_filled_data.get('DearnessAllowance', 0)
                val_perm_vacant = perm_vacant_data.get('DearnessAllowance', 0)
                val_temp_vacant = temp_vacant_data.get('DearnessAllowance', 0)
            elif label == 'स्था.पु.भ.':
                metric_key_for_comp = 'स्था.पु.भ.'
                val_perm_filled = perm_filled_data.get('LocalSupplemetoryAllowance', 0)
                val_temp_filled = temp_filled_data.get('LocalSupplemetoryAllowance', 0)
                val_perm_vacant = perm_vacant_data.get('LocalSupplemetoryAllowance', 0)
                val_temp_vacant = temp_vacant_data.get('LocalSupplemetoryAllowance', 0)
            elif label == 'घरभाडे':
                metric_key_for_comp = 'घरभाडे'
                val_perm_filled = perm_filled_data.get('HouseRentAllowance', 0)
                val_temp_filled = temp_filled_data.get('HouseRentAllowance', 0)
                val_perm_vacant = perm_vacant_data.get('HouseRentAllowance', 0)
                val_temp_vacant = temp_vacant_data.get('HouseRentAllowance', 0)
            elif label == 'प्रवास भत्ता':
                metric_key_for_comp = 'प्रवास भत्ता'
                val_perm_filled = perm_filled_data.get('TravelAllowance', 0)
                val_temp_filled = temp_filled_data.get('TravelAllowance', 0)
                val_perm_vacant = perm_vacant_data.get('TravelAllowance', 0)
                val_temp_vacant = temp_vacant_data.get('TravelAllowance', 0)
            elif label == 'इतर':
                metric_key_for_comp = 'इतर'
                val_perm_filled = perm_filled_data.get('Other', 0)
                val_temp_filled = temp_filled_data.get('Other', 0)
                val_perm_vacant = perm_vacant_data.get('Other', 0)
                val_temp_vacant = temp_vacant_data.get('Other', 0)
            elif label == 'एकूण खर्च':
                metric_key_for_comp = 'एकूण खर्च'
                val_perm_filled = sum(perm_filled_data.get(k, 0) for k in cost_fields)
                val_temp_filled = sum(temp_filled_data.get(k, 0) for k in cost_fields)
                val_perm_vacant = sum(perm_vacant_data.get(k, 0) for k in cost_fields)
                val_temp_vacant = sum(temp_vacant_data.get(k, 0) for k in cost_fields)
            
            perm_row[f'Filled_{class_key}'] = val_perm_filled
            perm_row[f'Vacant_{class_key}'] = val_perm_vacant
            temp_row[f'Filled_{class_key}'] = val_temp_filled
            temp_row[f'Vacant_{class_key}'] = val_temp_vacant
            
            if not is_total_col and metric_key_for_comp:
                if metric_key_for_comp == 'पदे':
                    perm_category_totals[metric_key_for_comp] += val_perm_filled + val_perm_vacant
                    temp_category_totals[metric_key_for_comp] += val_temp_filled + val_temp_vacant
                else:
                    perm_category_totals[metric_key_for_comp] += val_perm_filled
                    temp_category_totals[metric_key_for_comp] += val_temp_filled
        
        perm_row['Category_Total'] = perm_category_totals.get(metric_key_for_comp, 0)
        temp_row['Category_Total'] = temp_category_totals.get(metric_key_for_comp, 0)
        permanent_metric_rows.append(perm_row)
        temporary_metric_rows.append(temp_row)
        if metric_key_for_comp and metric_key_for_comp not in comparison_metrics_keys:
            comparison_metrics_keys.append(metric_key_for_comp)
    
    grand_totals_comparison = defaultdict(int)
    for key in comparison_metrics_keys:
        grand_totals_comparison[key] = perm_category_totals.get(key, 0) + temp_category_totals.get(key, 0)
    comparison_summary = [
        {'वर्ग': 'स्थायी', **perm_category_totals},
        {'वर्ग': 'अस्थायी', **temp_category_totals},
        {'वर्ग': 'एकूण', **grand_totals_comparison}
    ]
    
    final_class_summary = []
    grand_total_amt = 0
    grand_total_post = 0
    for cat in ['Permanent', 'Temporary']:
        cat_label = 'स्थायी' if cat == 'Permanent' else 'अस्थायी'
        cat_total_amt = 0
        cat_total_post = 0
        for cls_key in VALID_CLASS_KEYS:
            cls_mr = CLASS_MR_MAP.get(cls_key, cls_key)
            filled_data = summary.get(cat, {}).get(cls_mr, {}).get('Filled', defaultdict(int))
            vacant_data = summary.get(cat, {}).get(cls_mr, {}).get('Vacant', defaultdict(int))
            class_cat_total_amt = sum(filled_data.get(k, 0) for k in cost_fields)
            class_cat_total_post = filled_data.get('Posts', 0) + vacant_data.get('Posts', 0)
            final_class_summary.append({
                "CategoryLabel": cat_label,
                "ClassKey": cls_mr,
                "Amt": class_cat_total_amt,
                "Post": class_cat_total_post
            })
            cat_total_amt += class_cat_total_amt
            cat_total_post += class_cat_total_post
        final_class_summary.append({
            "CategoryLabel": cat_label,
            "ClassKey": "एकूण",
            "Amt": cat_total_amt,
            "Post": cat_total_post,
            "is_total": True
        })
        grand_total_amt += cat_total_amt
        grand_total_post += cat_total_post
    final_class_summary.append({
        "CategoryLabel": "स्थायी + अस्थायी",
        "ClassKey": "",
        "Amt": grand_total_amt,
        "Post": grand_total_post,
        "is_grand_total": True
    })
    
    return {
        'permanent_metric_rows': permanent_metric_rows,
        'temporary_metric_rows': temporary_metric_rows,
        'comparison_summary': comparison_summary,
        'comparison_metrics_keys': comparison_metrics_keys,
        'final_class_summary_table': final_class_summary,
        'grand_totals_comparison': dict(grand_totals_comparison)
    }

@ttl_cache(ttl_seconds=180, use_global=True)
def get_post_status_summary_data(db: Session, fiscal_year: str = '2025-26', district: Optional[str] = None) -> Dict[str, Any]:
    """Unified function for both district and overall post status summary data"""
    try:
        query_results = db.query(
            PostStatus.category, PostStatus.class_type, PostStatus.status,
            func.sum(PostStatus.posts).label("posts"),
            func.sum(PostStatus.salary).label("salary"),
            func.sum(PostStatus.grade_pay).label("grade_pay"),
            func.sum(PostStatus.dearness_allowance).label("dearness_allowance"),
            func.sum(PostStatus.special_pay).label("special_pay"),
            func.sum(PostStatus.local_supplementary_allowance).label("local_supplementary_allowance"),
            func.sum(PostStatus.house_rent_allowance).label("house_rent_allowance"),
            func.sum(PostStatus.travel_allowance).label("travel_allowance"),
            func.sum(PostStatus.other).label("other")
        ).filter(PostStatus.fiscal_year == fiscal_year)
        
        if district:
            query_results = query_results.filter(PostStatus.district == district)
        else:
            query_results = query_results.filter(PostStatus.district != DCO_STAFF_IDENTIFIER)
        
        query_results = query_results.group_by(PostStatus.category, PostStatus.class_type, PostStatus.status).all()
        
        summary = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(int))))
        for row in query_results:
            category = row.category
            raw_class = row.class_type
            status = row.status
            class_key = CLASS_MAPPING.get(raw_class)
            if not category or not class_key or not status:
                continue
            
            class_key_mr = CLASS_MR_MAP.get(class_key, class_key)
            target = summary[category][class_key_mr][status]
            for db_key in METRICS_DB_KEYS:
                target[db_key] = int(getattr(row, db_key) or 0)
            target['Posts'] = target.get('posts', 0)
            target['Salary'] = target.get('salary', 0)
            target['GradePay'] = target.get('grade_pay', 0)
            target['SpecialPay'] = target.get('special_pay', 0)
            target['DearnessAllowance'] = target.get('dearness_allowance', 0)
            target['LocalSupplemetoryAllowance'] = target.get('local_supplementary_allowance', 0)
            target['HouseRentAllowance'] = target.get('house_rent_allowance', 0)
            target['TravelAllowance'] = target.get('travel_allowance', 0)
            target['Other'] = target.get('other', 0)
        
        processed = _process_summary_data(summary, fiscal_year, district)
        
        district_rows = db.query(
            PostStatus.district, PostStatus.status,
            func.sum(PostStatus.posts).label('posts'),
            func.sum(PostStatus.salary).label('salary'),
            func.sum(PostStatus.grade_pay).label('grade_pay'),
            func.sum(PostStatus.special_pay).label('special_pay'),
            func.sum(PostStatus.dearness_allowance).label('dearness_allowance'),
            func.sum(PostStatus.local_supplementary_allowance).label('local_supplementary_allowance'),
            func.sum(PostStatus.house_rent_allowance).label('house_rent_allowance'),
            func.sum(PostStatus.travel_allowance).label('travel_allowance'),
            func.sum(PostStatus.other).label('other')
        ).filter(PostStatus.fiscal_year == fiscal_year)
        
        if district:
            district_rows = district_rows.filter(PostStatus.district == district)
        else:
            district_rows = district_rows.filter(PostStatus.district != DCO_STAFF_IDENTIFIER)
        
        district_rows = district_rows.group_by(PostStatus.district, PostStatus.status).all()
        
        district_summary = defaultdict(lambda: {"Filled": {"Posts": 0}, "Vacant": {"Posts": 0}, "TotalCost": 0})
        district_components_sums = defaultdict(lambda: {"Salary": 0, "GradePay": 0, "SpecialPay": 0, "Allowances": 0})
        
        for r in district_rows:
            d = getattr(r, 'district', None) or ''
            st = getattr(r, 'status', None) or ''
            posts_sum = int(getattr(r, 'posts', 0) or 0)
            if st in ('Filled', 'Vacant'):
                district_summary[d][st]['Posts'] += posts_sum
            
            salary = int(getattr(r, 'salary', 0) or 0)
            grade = int(getattr(r, 'grade_pay', 0) or 0)
            special = int(getattr(r, 'special_pay', 0) or 0)
            da = int(getattr(r, 'dearness_allowance', 0) or 0)
            lsa = int(getattr(r, 'local_supplementary_allowance', 0) or 0)
            hra = int(getattr(r, 'house_rent_allowance', 0) or 0)
            travel = int(getattr(r, 'travel_allowance', 0) or 0)
            other = int(getattr(r, 'other', 0) or 0)
            allowances_total = da + lsa + hra + travel + other
            cost = salary + grade + special + allowances_total
            
            district_summary[d]['TotalCost'] += cost
            dc = district_components_sums[d]
            dc['Salary'] += salary
            dc['GradePay'] += grade
            dc['SpecialPay'] += special
            dc['Allowances'] += allowances_total
        
        district_category_rows = db.query(
            PostStatus.district, PostStatus.category, func.sum(PostStatus.posts).label('posts')
        ).filter(PostStatus.fiscal_year == fiscal_year)
        
        if district:
            district_category_rows = district_category_rows.filter(PostStatus.district == district)
        else:
            district_category_rows = district_category_rows.filter(PostStatus.district != DCO_STAFF_IDENTIFIER)
        
        district_category_rows = district_category_rows.group_by(PostStatus.district, PostStatus.category).all()
        district_category_posts = defaultdict(lambda: {'Permanent': 0, 'Temporary': 0})
        
        for r in district_category_rows:
            d = getattr(r, 'district', None) or ''
            c = getattr(r, 'category', None) or ''
            p = int(getattr(r, 'posts', 0) or 0)
            if c in ('Permanent', 'Temporary'):
                district_category_posts[d][c] += p
        
        return {
            **processed,
            'raw_summary_dict': summary,
            'class_keys_order': [CLASS_MR_MAP.get(k, k) for k in VALID_CLASS_KEYS],
            'district_summary': district_summary,
            'district_components_sums': district_components_sums,
            'district_category_posts': district_category_posts
        }
    
    except Exception as e:
        logger.error(f"Error fetching/processing post status summary data (district={district}): {e}", exc_info=True)
        return None

def get_district_post_status_summary_data(db: Session, district: str, fiscal_year: str = '2025-26') -> Dict[str, Any]:
    """Backward compatibility wrapper"""
    return get_post_status_summary_data(db, fiscal_year, district=district)

@router.get("/api/statuses", response_class=JSONResponse)
async def api_get_statuses(
    request: Request,
    district: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    cls: Optional[str] = Query(None, alias="class"),
    db: Session = Depends(get_db)
):
    fiscal_year = get_fiscal_year_from_request(request, db)
    _, sub_scheme = get_scheme_from_cookies(request)
    query = db.query(PostStatus.status).distinct().filter(
        PostStatus.fiscal_year == fiscal_year,
        PostStatus.sub_scheme_code == sub_scheme
    )
    if district:
        query = query.filter(PostStatus.district == district)
    if category:
        query = query.filter(PostStatus.category == category)
    if cls:
        query = query.filter(PostStatus.class_type == cls)
    statuses = [row[0] for row in query.order_by(PostStatus.status).all()]
    return JSONResponse({"statuses": statuses})

@router.get("/api/record-data", response_class=JSONResponse)
async def api_get_record_data(
    request: Request,
    district: str = Query(...),
    category: str = Query(...),
    cls: str = Query(..., alias="class"),
    status: str = Query(...),
    db: Session = Depends(get_db)
):
    fiscal_year = get_fiscal_year_from_request(request, db)
    _, sub_scheme = get_scheme_from_cookies(request)
    record = db.query(PostStatus).filter(
        PostStatus.fiscal_year == fiscal_year,
        PostStatus.sub_scheme_code == sub_scheme,
        PostStatus.district == district,
        PostStatus.category == category,
        PostStatus.class_type == cls,
        PostStatus.status == status
    ).first()
    
    if not record:
        return JSONResponse({"found": False})
    
    return JSONResponse({
        "found": True, "id": record.id,
        "posts": record.posts or 0,
        "salary": record.salary or 0,
        "grade_pay": record.grade_pay or 0,
        "special_pay": record.special_pay or 0,
        "dearness_allowance": record.dearness_allowance or 0,
        "local_supplementary_allowance": record.local_supplementary_allowance or 0,
        "house_rent_allowance": record.house_rent_allowance or 0,
        "travel_allowance": record.travel_allowance or 0,
        "other": record.other or 0
    })

@router.post("/api/update-inline", response_class=JSONResponse)
async def api_update_inline(
    request: Request,
    db: Session = Depends(get_db),
    id: int = Form(...),
    Posts: int = Form(0),
    Salary: int = Form(0),
    GradePay: int = Form(0),
    SpecialPay: int = Form(0),
    DearnessAllowance: int = Form(0),
    LocalSupplemetoryAllowance: int = Form(0),
    HouseRentAllowance: int = Form(0),
    TravelAllowance: int = Form(0),
    Other: int = Form(0)
):
    auth_role = request.cookies.get('auth_role', '')
    auth_level = request.cookies.get('auth_level', '')
    auth_unit = get_auth_unit(request)
    auth_user = request.cookies.get('auth_user', '')
    
    if not check_edit_permission_for_scheme(auth_role, auth_level, auth_unit, db):
        return JSONResponse({"success": False, "message": "Forbidden"}, status_code=403)
    
    is_allowed, timing_msg = check_data_filling_allowed(db, auth_level, auth_role, SCHEME_CONFIG.code)
    if not is_allowed:
        return JSONResponse({"success": False, "message": timing_msg or "Data filling period expired"}, status_code=403)
    
    _, sub_scheme = get_scheme_from_cookies(request)
    record = db.query(PostStatus).filter(
        PostStatus.id == id,
        PostStatus.sub_scheme_code == sub_scheme
    ).first()
    if not record:
        return JSONResponse({"success": False, "message": "Record not found"}, status_code=404)
    
    allowed, error_msg = validate_access_control(record.district, auth_level, auth_unit, db)
    if not allowed:
        return JSONResponse({"success": False, "message": error_msg}, status_code=403)
    
    values_to_check = [Posts, Salary, GradePay, SpecialPay, DearnessAllowance, LocalSupplemetoryAllowance, HouseRentAllowance, TravelAllowance, Other]
    is_valid, error_msg = validate_numeric_inputs(*values_to_check)
    if not is_valid:
        return JSONResponse({"success": False, "message": error_msg}, status_code=400)
    
    old_values = {
        "posts": record.posts, "salary": record.salary, "grade_pay": record.grade_pay,
        "special_pay": record.special_pay, "dearness_allowance": record.dearness_allowance,
        "local_supplementary_allowance": record.local_supplementary_allowance,
        "house_rent_allowance": record.house_rent_allowance,
        "travel_allowance": record.travel_allowance, "other": record.other
    }
    
    record.posts = Posts
    record.salary = Salary
    record.grade_pay = GradePay
    record.special_pay = SpecialPay
    record.dearness_allowance = DearnessAllowance
    record.local_supplementary_allowance = LocalSupplemetoryAllowance
    record.house_rent_allowance = HouseRentAllowance
    record.travel_allowance = TravelAllowance
    record.other = Other
    
    new_values = {
        "posts": Posts, "salary": Salary, "grade_pay": GradePay, "special_pay": SpecialPay,
        "dearness_allowance": DearnessAllowance, "local_supplementary_allowance": LocalSupplemetoryAllowance,
        "house_rent_allowance": HouseRentAllowance, "travel_allowance": TravelAllowance, "other": Other
    }
    
    try:
        AuditService.log_edit(db, request, "post_status", id, auth_user, old_values, new_values)
    except Exception:
        pass
    
    db.commit()
    try:
        from src.routers.ui_taluka_selection import invalidate_district_status_cache
        scheme_code, _ = get_scheme_from_cookies(request)
        invalidate_district_status_cache(scheme_code, record.fiscal_year)
    except Exception:
        pass
    return JSONResponse({"success": True, "message": "अपडेट यशस्वी"})

@router.get("", response_class=HTMLResponse)
async def ui_list_post_status(
    request: Request,
    db: Session = Depends(get_db),
    view: Optional[str] = Query("edit"),
    district: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    cls: Optional[str] = Query(None, alias="class"),
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500)
):
    auth_role = request.cookies.get('auth_role', '')
    auth_level = request.cookies.get('auth_level', '')
    auth_unit = get_auth_unit(request)

    if auth_level == 'district' and auth_unit:
        districts_for_filter = [auth_unit]
    elif auth_level == 'dco':
        districts_for_filter = DISTRICTS
    else:
        districts_for_filter = REGULAR_DISTRICTS
    
    context = {
        "request": request,
        "resource_name": "प्रपत्र क",
        "districts": districts_for_filter,
        "categories": CATEGORIES,
        "classes": CLASSES_SHEET1_2,
        "statuses": STATUSES,
        "current_district": district,
        "current_category": category,
        "current_class": cls,
        "current_status": status_filter,
        "view_mode": view,
        "districts_mr": DISTRICTS_MR,
        "categories_mr": CATEGORIES_MR,
        "classes_mr": CLASSES_MR,
        "statuses_mr": STATUSES_MR,
        "auth_level": auth_level,
        "relative_years": get_relative_fiscal_years(get_fiscal_year_from_request(request, db))
    }

    if view == "summary":
        fiscal_year = get_fiscal_year_from_request(request, db)
        if auth_level == 'district' and auth_unit:
            summary_data = get_post_status_summary_data(db, fiscal_year, district=auth_unit)
        elif auth_level == 'taluka' and auth_unit:
            district_name = get_district_from_taluka(auth_unit)
            summary_data = get_post_status_summary_data(db, fiscal_year, district=district_name) if district_name else None
        else:
            summary_data = get_post_status_summary_data(db, fiscal_year)
        
        if not summary_data:
            raise HTTPException(status_code=500, detail="Could not generate Post Status summary data.")

        district_summary = summary_data.get('district_summary', {})
        
        if auth_level == 'district' and auth_unit:
            labels = [auth_unit]
        elif auth_level == 'taluka' and auth_unit:
            district_name = get_district_from_taluka(auth_unit)
            labels = [district_name] if district_name else []
        elif auth_level == 'dco':
            labels = DISTRICTS
        else:
            labels = REGULAR_DISTRICTS
        
        chart_data = {}
        try:
            dist_filled = []
            dist_vacant = []
            dist_cost = []
            dist_salary = []
            dist_grade = []
            dist_special = []
            dist_allowances = []
            for d in labels:
                ds = district_summary.get(d, {})
                dcomp = summary_data.get('district_components_sums', {}).get(d, {})
                dist_filled.append(int(ds.get('Filled', {}).get('Posts', 0) or 0))
                dist_vacant.append(int(ds.get('Vacant', {}).get('Posts', 0) or 0))
                dist_cost.append(int(ds.get('TotalCost', 0) or 0))
                dist_salary.append(int(dcomp.get('Salary', 0) or 0))
                dist_grade.append(int(dcomp.get('GradePay', 0) or 0))
                dist_special.append(int(dcomp.get('SpecialPay', 0) or 0))
                dist_allowances.append(int(dcomp.get('Allowances', 0) or 0))
            
            if not any(v > 0 for v in dist_filled + dist_vacant + dist_cost + dist_salary + dist_grade + dist_special + dist_allowances):
                dyn_labels = list(district_summary.keys())
                dist_filled = [int((district_summary.get(d, {}).get('Filled', {}) or {}).get('Posts', 0) or 0) for d in dyn_labels]
                dist_vacant = [int((district_summary.get(d, {}).get('Vacant', {}) or {}).get('Posts', 0) or 0) for d in dyn_labels]
                dist_cost = [int((district_summary.get(d, {}) or {}).get('TotalCost', 0) or 0) for d in dyn_labels]
                dist_salary = [int((summary_data.get('district_components_sums', {}).get(d, {}) or {}).get('Salary', 0) or 0) for d in dyn_labels]
                dist_grade = [int((summary_data.get('district_components_sums', {}).get(d, {}) or {}).get('GradePay', 0) or 0) for d in dyn_labels]
                dist_special = [int((summary_data.get('district_components_sums', {}).get(d, {}) or {}).get('SpecialPay', 0) or 0) for d in dyn_labels]
                dist_allowances = [int((summary_data.get('district_components_sums', {}).get(d, {}) or {}).get('Allowances', 0) or 0) for d in dyn_labels]
                labels = dyn_labels

            if labels:
                chart_data['district_posts_by_status'] = {'labels': labels, 'भरलेली': dist_filled, 'रिक्त': dist_vacant}
                chart_data['district_total_cost'] = {'labels': labels, 'values': dist_cost}
                chart_data['district_allowance_breakdown'] = {
                    'labels': labels,
                    'Salary': dist_salary,
                    'GradePay': dist_grade,
                    'SpecialPay': dist_special,
                    'Allowances': dist_allowances
                }
                
                dcmap = summary_data.get('district_category_posts', {})
                chart_data['district_category_posts'] = {
                    'labels': labels,
                    'Permanent': [int((dcmap.get(d, {}) or {}).get('Permanent', 0) or 0) for d in labels],
                    'Temporary': [int((dcmap.get(d, {}) or {}).get('Temporary', 0) or 0) for d in labels]
                }

        except Exception as e:
            logger.error(f"Error preparing chart data for Post Status: {e}", exc_info=True)
            chart_data = {}

        context.update({
            "resource_name": "प्रपत्र क गोषवारा",
            "chart_data": chart_data,
            "chart_data_json": json.dumps(chart_data) if chart_data else "{}",
            "auth_unit": auth_unit
        })
        context.update(summary_data)
        response = templates.TemplateResponse("schemes/s2029/subs/s20290182/post_status_list.html", context)
        response.headers.update(get_no_cache_headers())
        return response

    elif view == "edit":
        fiscal_year = get_fiscal_year_from_request(request, db)
        _, sub_scheme = get_scheme_from_cookies(request)
        can_edit = check_edit_permission_for_scheme(auth_role, auth_level, auth_unit, db)
        query = build_district_filter(db.query(PostStatus), auth_level, auth_unit, PostStatus).filter(
            PostStatus.fiscal_year == fiscal_year,
            PostStatus.sub_scheme_code == sub_scheme
        )
        
        if district:
            query = query.filter(PostStatus.district == district)
        if category:
            query = query.filter(PostStatus.category == category)
        if cls:
            query = query.filter(PostStatus.class_type == cls)
        if status_filter:
            query = query.filter(PostStatus.status == status_filter)
        
        total_count = query.with_entities(func.count()).scalar()
        items = query.order_by(PostStatus.id).offset((page - 1) * page_size).limit(page_size).all()
        
        filtered_params = {k: v for k, v in {"district": district, "category": category, "class": cls, "status": status_filter}.items() if v}
        context["export_query_string_list"] = "?" + urlencode(filtered_params) if filtered_params else ""
        context["items"] = items
        context["total_count"] = total_count
        context["page"] = page
        context["page_size"] = page_size
        context["chart_data"] = None
        context["can_edit"] = can_edit
        response = templates.TemplateResponse("schemes/s2029/subs/s20290182/post_status_list.html", context)
        response.headers.update(get_no_cache_headers())
        return response

    else:
        raise HTTPException(status_code=400, detail="Invalid view parameter. Use 'edit' or 'summary'.")

@router.get("/{id}/edit", response_class=HTMLResponse)
async def ui_edit_post_status_form(request: Request, id: int, db: Session = Depends(get_db)):
    auth_level = request.cookies.get('auth_level')
    auth_role = request.cookies.get('auth_role')
    auth_unit = get_auth_unit(request)
    
    is_allowed, timing_msg = check_data_filling_allowed(db, auth_level, auth_role, SCHEME_CONFIG.code)
    if not is_allowed and auth_role == 'assistant':
        raise HTTPException(status_code=403, detail=timing_msg or "Data filling period has expired")
    
    if auth_level == 'district' and auth_unit:
        districts_for_filter = [auth_unit]
    elif auth_level == 'dco':
        districts_for_filter = DISTRICTS
    else:
        districts_for_filter = REGULAR_DISTRICTS
    
    _, sub_scheme = get_scheme_from_cookies(request)
    item = db.query(PostStatus).filter(
        PostStatus.id == id,
        PostStatus.sub_scheme_code == sub_scheme
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail=f"प्रपत्र क ID {id} सापडला नाही")
    
    return templates.TemplateResponse("schemes/s2029/subs/s20290182/post_status_form.html", {
        "request": request,
        "districts": districts_for_filter,
        "categories": CATEGORIES,
        "classes": CLASSES_SHEET1_2,
        "statuses": STATUSES,
        "item": item,
        "resource_name": "प्रपत्र क संपादन",
        "districts_mr": DISTRICTS_MR,
        "categories_mr": CATEGORIES_MR,
        "classes_mr": CLASSES_MR,
        "statuses_mr": STATUSES_MR,
        "auth_level": auth_level
    })

@router.post("/{id}/edit", response_class=RedirectResponse)
async def ui_update_post_status(
    request: Request,
    id: int,
    db: Session = Depends(get_db),
    District: str = Form(...),
    Category: str = Form(...),
    Class: str = Form(...),
    Status: str = Form(...),
    Posts: Optional[int] = Form(None),
    Salary: Optional[int] = Form(None),
    GradePay: Optional[int] = Form(None),
    SpecialPay: Optional[int] = Form(None),
    DearnessAllowance: Optional[int] = Form(None),
    LocalSupplemetoryAllowance: Optional[int] = Form(None),
    HouseRentAllowance: Optional[int] = Form(None),
    TravelAllowance: Optional[int] = Form(None),
    Other: Optional[int] = Form(None)
):
    auth_role = request.cookies.get('auth_role') or ''
    auth_level = request.cookies.get('auth_level') or ''
    auth_unit = get_auth_unit(request) or ''
    
    if auth_role in ("officer1", "officer2", "dco"):
        raise HTTPException(status_code=403, detail="Forbidden")
    if auth_level == 'taluka' and auth_unit:
        if District != get_district_from_taluka_name(auth_unit):
            raise HTTPException(status_code=400, detail="Invalid district for taluka user")
    
    is_allowed, timing_msg = check_data_filling_allowed(db, auth_level, auth_role, SCHEME_CONFIG.code)
    if not is_allowed:
        raise HTTPException(status_code=403, detail=timing_msg or "Data filling period has expired")
    
    _, sub_scheme = get_scheme_from_cookies(request)
    db_item = db.query(PostStatus).filter(
        PostStatus.id == id,
        PostStatus.sub_scheme_code == sub_scheme
    ).first()
    if not db_item:
        raise HTTPException(status_code=404, detail=f"प्रपत्र क ID {id} सापडला नाही")
    
    try:
        update_dict = {
            "district": District, "category": Category, "class_type": Class, "status": Status,
            "posts": Posts, "salary": Salary, "grade_pay": GradePay, "special_pay": SpecialPay,
            "dearness_allowance": DearnessAllowance, "local_supplementary_allowance": LocalSupplemetoryAllowance,
            "house_rent_allowance": HouseRentAllowance, "travel_allowance": TravelAllowance, "other": Other
        }
        for key, value in update_dict.items():
            if value is not None and hasattr(db_item, key):
                setattr(db_item, key, value)
        db.commit()
        db.refresh(db_item)
        try:
            from src.routers.ui_taluka_selection import invalidate_district_status_cache
            scheme_code, _ = get_scheme_from_cookies(request)
            invalidate_district_status_cache(scheme_code, db_item.fiscal_year)
        except Exception:
            pass
        return RedirectResponse(
            url=router.url_path_for("ui_list_post_status") + "?view=edit",
            status_code=status.HTTP_303_SEE_OTHER
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update Post Status ID {id}: {e}", exc_info=True)
        districts_for_filter = DISTRICTS
        if auth_level == 'district' and auth_unit:
            districts_for_filter = [auth_unit]
        return templates.TemplateResponse("schemes/s2029/subs/s20290182/post_status_form.html", {
            "request": request,
            "error": f"रेकॉर्ड अपडेट करण्यात अयशस्वी: {e}",
            "districts": districts_for_filter,
            "categories": CATEGORIES,
            "classes": CLASSES_SHEET1_2,
            "statuses": STATUSES,
            "item": db_item,
            "resource_name": "प्रपत्र क संपादन",
            "districts_mr": DISTRICTS_MR,
            "categories_mr": CATEGORIES_MR,
            "classes_mr": CLASSES_MR,
            "statuses_mr": STATUSES_MR,
            "auth_level": auth_level
        }, status_code=400)

@router.get("/summary/export-excel", response_class=StreamingResponse)
async def export_post_status_summary_excel(request: Request, db: Session = Depends(get_db)):
    fiscal_year = get_fiscal_year_from_request(request, db)
    summary_data = get_post_status_summary_data(db, fiscal_year)
    if summary_data is None:
        raise HTTPException(status_code=500, detail="Could not generate summary data for download.")
    
    try:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            CLASS_KEYS_ORDER = ['वर्ग-1 व 2', 'वर्ग-3', 'वर्ग-4', 'एकूण']
            METRICS_ORDER_COMP = summary_data.get('comparison_metrics_keys', [])
            
            perm_rows_df = pd.DataFrame(summary_data['permanent_metric_rows'])
            cols_perm = ['Label'] + [f'{stat}_{cls}' for stat in ['Filled', 'Vacant'] for cls in CLASS_KEYS_ORDER] + ['Category_Total']
            perm_rows_df = perm_rows_df[cols_perm]
            perm_rows_df.to_excel(writer, sheet_name='Permanent Posts Summary', index=False)
            
            temp_rows_df = pd.DataFrame(summary_data['temporary_metric_rows'])
            cols_temp = ['Label'] + [f'{stat}_{cls}' for stat in ['Filled', 'Vacant'] for cls in CLASS_KEYS_ORDER] + ['Category_Total']
            temp_rows_df = temp_rows_df[cols_temp]
            temp_rows_df.to_excel(writer, sheet_name='Temporary Posts Summary', index=False)
            
            comp_df = pd.DataFrame(summary_data['comparison_summary'])
            if METRICS_ORDER_COMP:
                comp_df = comp_df[['वर्ग'] + METRICS_ORDER_COMP]
            comp_df.to_excel(writer, sheet_name='Overall Comparison', index=False)
            
            final_sum_df = pd.DataFrame(summary_data['final_class_summary_table'])
            final_sum_df = final_sum_df[['CategoryLabel', 'ClassKey', 'Amt', 'Post']]
            final_sum_df.columns = ['Category', 'Class', 'Amount', 'Posts']
            final_sum_df.to_excel(writer, sheet_name='Final Class Summary', index=False)
        
        output.seek(0)
        headers = {'Content-Disposition': 'attachment; filename="post_status_summary_report.xlsx"'}
        return StreamingResponse(
            output,
            headers=headers,
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        logger.error(f"Failed to generate Post Status Summary Excel file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Could not generate Excel file: {e}")

@router.get("/list/export-excel", response_class=StreamingResponse)
async def export_post_status_list_excel(
    request: Request,
    db: Session = Depends(get_db),
    district: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    cls: Optional[str] = Query(None, alias="class"),
    status_filter: Optional[str] = Query(None, alias="status")
):
    fiscal_year = get_fiscal_year_from_request(request, db)
    _, sub_scheme = get_scheme_from_cookies(request)
    query = db.query(PostStatus).filter(
        PostStatus.fiscal_year == fiscal_year,
        PostStatus.sub_scheme_code == sub_scheme
    )
    if district:
        query = query.filter(PostStatus.district == district)
    if category:
        query = query.filter(PostStatus.category == category)
    if cls:
        query = query.filter(PostStatus.class_type == cls)
    if status_filter:
        query = query.filter(PostStatus.status == status_filter)
    
    items = query.order_by(PostStatus.id).all()
    data_dict_list = []
    if items:
        columns = [c.name for c in PostStatus.__table__.columns]
        for item in items:
            data_dict_list.append({col: getattr(item, col, None) for col in columns})
    
    df = pd.DataFrame(data_dict_list)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Post Status List', index=False)
    output.seek(0)
    headers = {'Content-Disposition': 'attachment; filename="post_status_list.xlsx"'}
    return StreamingResponse(
        output,
        headers=headers,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@router.get("/export-original", response_class=StreamingResponse)
async def export_post_status_original(
    request: Request,
    db: Session = Depends(get_db),
    district: Optional[str] = Query(None)
):
    auth_level = request.cookies.get('auth_level')
    auth_unit = get_auth_unit(request)
    user_district = auth_unit if auth_level == 'district' else (district if auth_level in ('dco', 'officer1', 'officer2') else None)
    _, sub_scheme = get_scheme_from_cookies(request)
    fiscal_year = get_fy(request, db)
    return await export_original_workbook_async(db, user_district=user_district, sub_scheme_code=sub_scheme, fiscal_year=fiscal_year)

@router.get("/export-sheet-only", response_class=StreamingResponse)
async def export_post_status_sheet_only(
    request: Request,
    db: Session = Depends(get_db),
    district: Optional[str] = Query(None)
):
    auth_level = request.cookies.get('auth_level')
    auth_unit = get_auth_unit(request)
    user_district = auth_unit if auth_level == 'district' else (district if auth_level in ('dco', 'officer1', 'officer2') else None)
    _, sub_scheme = get_scheme_from_cookies(request)
    fiscal_year = get_fy(request, db)
    return await export_original_workbook_async(db, only_sheet="post_status", user_district=user_district, sub_scheme_code=sub_scheme, fiscal_year=fiscal_year)
