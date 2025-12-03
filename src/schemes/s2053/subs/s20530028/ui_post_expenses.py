from fastapi import APIRouter, Depends, Request, Form, HTTPException, status, Query
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, Dict, Any
from urllib.parse import urlencode
from collections import defaultdict
import logging
import json

from src.database import get_db
from src.config import DISTRICTS, REGULAR_DISTRICTS, DCO_STAFF_IDENTIFIER, DISTRICTS_MR
from src.utils_taluka import is_taluka_allowed, get_district_from_taluka_name
from src.utils_district import build_district_filter, get_district_from_taluka, check_edit_permission
from src.utils_fiscal_year import get_fiscal_year_from_request
from src.utils_scheme import get_scheme_from_cookies
from src.utils_cache import ttl_cache
from src.excel_template_export import export_original_workbook
from .models import PostExpenses, SUB_SCHEME_CODE
from .config import CATEGORIES, CLASSES_SHEET3, POST_EXPENSES_DISTRICT_COMPONENT_FIELD, CATEGORIES_MR, CLASSES_SHEET3_MR



templates = Jinja2Templates(directory="templates")

router = APIRouter(
    prefix="/ui/post-expenses",
    tags=["UI - प्रपत्र ब"],
    include_in_schema=False
)

logger = logging.getLogger(__name__)

@router.get("/api/classes", response_class=JSONResponse)
async def api_get_classes(request: Request, district: Optional[str] = Query(None), category: Optional[str] = Query(None), db: Session = Depends(get_db)):
    fiscal_year = get_fiscal_year_from_request(request, db)
    query = db.query(PostExpenses.class_type).distinct().filter(PostExpenses.fiscal_year == fiscal_year)
    if district:
        query = query.filter(PostExpenses.district == district)
    if category:
        query = query.filter(PostExpenses.category == category)
    classes = [row[0] for row in query.order_by(PostExpenses.class_type).all()]
    return JSONResponse({"classes": classes})

@router.get("/api/record-data", response_class=JSONResponse)
async def api_get_record_data(request: Request, district: str = Query(...), category: str = Query(...), cls: str = Query(..., alias="class"), db: Session = Depends(get_db)):
    fiscal_year = get_fiscal_year_from_request(request, db)
    record = db.query(PostExpenses).filter(
        PostExpenses.fiscal_year == fiscal_year,
        PostExpenses.district == district,
        PostExpenses.category == category,
        PostExpenses.class_type == cls
    ).first()
    
    if not record:
        return JSONResponse({"found": False})
    
    return JSONResponse({
        "found": True, "id": record.id,
        "filled_posts": record.filled_posts or 0,
        "vacant_posts": record.vacant_posts or 0,
        "medical_expenses": record.medical_expenses or 0,
        "festival_advance": record.festival_advance or 0,
        "swagram_maharashtra_darshan": record.swagram_maharashtra_darshan or 0,
        "seventh_pay_commission_difference_nps": record.seventh_pay_commission_difference_nps or 0,
        "nps": record.nps or 0,
        "seventh_pay_commission_difference": record.seventh_pay_commission_difference or 0,
        "other": record.other or 0
    })

@router.post("/api/update-inline", response_class=JSONResponse)
async def api_update_inline(request: Request, db: Session = Depends(get_db), id: int = Form(...), FilledPosts: int = Form(0), VacantPosts: int = Form(0), MedicalExpenses: int = Form(0), FestivalAdvance: int = Form(0), SwagramMaharashtraDarshan: int = Form(0), SeventhPayCommissionDifferenceNps: int = Form(0), Nps: int = Form(0), SeventhPayCommissionDifference: int = Form(0), Other: int = Form(0)):
    from src.utils_timing import check_data_filling_allowed
    from src.audit_service import AuditService
    
    auth_role = request.cookies.get('auth_role', '')
    auth_level = request.cookies.get('auth_level', '')
    auth_unit = request.cookies.get('auth_unit', '')
    auth_user = request.cookies.get('auth_user', '')
    
    if not check_edit_permission(auth_role, auth_level, auth_unit, db):
        return JSONResponse({"success": False, "message": "Forbidden"}, status_code=403)
    
    is_allowed, timing_msg = check_data_filling_allowed(db, auth_level, auth_role)
    if not is_allowed:
        return JSONResponse({"success": False, "message": timing_msg or "Data filling period expired"}, status_code=403)
    
    record = db.query(PostExpenses).filter(PostExpenses.id == id).first()
    if not record:
        return JSONResponse({"success": False, "message": "Record not found"}, status_code=404)
    
    if auth_level == 'district' and auth_unit:
        if auth_unit == DCO_STAFF_IDENTIFIER:
            if record.district != DCO_STAFF_IDENTIFIER:
                return JSONResponse({"success": False, "message": "Access denied"}, status_code=403)
        else:
            if record.district != auth_unit or record.district == DCO_STAFF_IDENTIFIER:
                return JSONResponse({"success": False, "message": "Access denied"}, status_code=403)
    
    if auth_level == 'taluka' and auth_unit:
        district_name = get_district_from_taluka(auth_unit)
        if not district_name or record.district != district_name or record.district == DCO_STAFF_IDENTIFIER:
            return JSONResponse({"success": False, "message": "Access denied"}, status_code=403)
    
    # Validate non-negative values and reasonable limits
    values_to_check = [FilledPosts, VacantPosts, MedicalExpenses, FestivalAdvance, SwagramMaharashtraDarshan, SeventhPayCommissionDifferenceNps, Nps, SeventhPayCommissionDifference, Other]
    if any(v < 0 for v in values_to_check):
        return JSONResponse({"success": False, "message": "नकारात्मक मूल्ये स्वीकार्य नाहीत"}, status_code=400)
    if any(v > 999999999 for v in values_to_check):
        return JSONResponse({"success": False, "message": "मूल्य खूप मोठे आहे"}, status_code=400)
    
    old_values = {"filled_posts": record.filled_posts, "vacant_posts": record.vacant_posts, "medical_expenses": record.medical_expenses, "festival_advance": record.festival_advance, "swagram_maharashtra_darshan": record.swagram_maharashtra_darshan, "seventh_pay_commission_difference_nps": record.seventh_pay_commission_difference_nps, "nps": record.nps, "seventh_pay_commission_difference": record.seventh_pay_commission_difference, "other": record.other}
    
    record.filled_posts = FilledPosts
    record.vacant_posts = VacantPosts
    record.medical_expenses = MedicalExpenses
    record.festival_advance = FestivalAdvance
    record.swagram_maharashtra_darshan = SwagramMaharashtraDarshan
    record.seventh_pay_commission_difference_nps = SeventhPayCommissionDifferenceNps
    record.nps = Nps
    record.seventh_pay_commission_difference = SeventhPayCommissionDifference
    record.other = Other
    
    new_values = {"filled_posts": FilledPosts, "vacant_posts": VacantPosts, "medical_expenses": MedicalExpenses, "festival_advance": FestivalAdvance, "swagram_maharashtra_darshan": SwagramMaharashtraDarshan, "seventh_pay_commission_difference_nps": SeventhPayCommissionDifferenceNps, "nps": Nps, "seventh_pay_commission_difference": SeventhPayCommissionDifference, "other": Other}
    
    try:
        AuditService.log_edit(db, request, "post_expenses", id, auth_user, old_values, new_values)
    except:
        pass
    
    db.commit()
    return JSONResponse({"success": True, "message": "अपडेट यशस्वी"})

@ttl_cache(ttl_seconds=180, use_global=True)
def get_district_post_expenses_summary_data(db: Session, district: str, fiscal_year: str) -> Dict[str, Any]:
    logger.info(f"--- (Helper REVISED v4.1) Fetching district post expenses summary data for {district} ---")
    try:
        post_counts_query = db.query(
            PostExpenses.class_type,
            PostExpenses.category,
            func.sum(PostExpenses.filled_posts).label("TotalFilled"),
            func.sum(PostExpenses.vacant_posts).label("TotalVacant")
        ).filter(
            PostExpenses.district == district,
            PostExpenses.fiscal_year == fiscal_year
        ).group_by(
            PostExpenses.class_type,
            PostExpenses.category
        ).all()
        logger.info(f"(Helper REVISED v4.1) District post counts query returned {len(post_counts_query)} rows.")

        expense_data_query = db.query(
            PostExpenses.district,
            PostExpenses.medical_expenses,
            PostExpenses.festival_advance,
            PostExpenses.swagram_maharashtra_darshan,
            PostExpenses.seventh_pay_commission_difference_nps,
            PostExpenses.nps,
            PostExpenses.seventh_pay_commission_difference,
            PostExpenses.other
        ).filter(
            PostExpenses.district == district,
            PostExpenses.fiscal_year == fiscal_year
        ).all()
        logger.info(f"(Helper REVISED v4.1) District expense data query returned {len(expense_data_query)} rows.")

        table1_data = defaultdict(lambda: defaultdict(int))
        for row in post_counts_query:
            cls = row.class_type
            cat = row.category
            if cls not in ['1', '2', '3', '4']: continue
            table1_data[cls][f"{cat}_Filled"] = int(row.TotalFilled or 0)
            table1_data[cls][f"{cat}_Vacant"] = int(row.TotalVacant or 0)

        table1_rows = []
        table1_totals = defaultdict(int)
        for i, cls in enumerate(['1', '2', '3', '4'], 1):
            row_data = {
                "SrNo": i,
                "Class": cls,
                "Permanent_Filled": table1_data[cls].get("Permanent_Filled", 0),
                "Permanent_Vacant": table1_data[cls].get("Permanent_Vacant", 0),
                "Temporary_Filled": table1_data[cls].get("Temporary_Filled", 0),
                "Temporary_Vacant": table1_data[cls].get("Temporary_Vacant", 0),
            }
            row_data["Row_Total"] = sum(row_data[k] for k in ["Permanent_Filled", "Permanent_Vacant", "Temporary_Filled", "Temporary_Vacant"])
            table1_rows.append(row_data)
            
            for key in ["Permanent_Filled", "Permanent_Vacant", "Temporary_Filled", "Temporary_Vacant", "Row_Total"]:
                table1_totals[key] += row_data[key]

        table1_totals["SrNo"] = "--"
        table1_totals["Class"] = "एकूण"

        table3_totals_dict = defaultdict(float)
        processed_districts = set()

        for row in expense_data_query:
            district_name = row.district
            if not district_name or district_name in processed_districts: continue
            
            processed_districts.add(district_name)
            table3_totals_dict['Medical'] += float(row.medical_expenses or 0.0)
            table3_totals_dict['Festival'] += float(row.festival_advance or 0.0)
            table3_totals_dict['Swagram'] += float(row.swagram_maharashtra_darshan or 0.0)
            pay_diff_nps = float(row.seventh_pay_commission_difference_nps or 0.0)
            nps = float(row.nps or 0.0)
            pay_diff = float(row.seventh_pay_commission_difference or 0.0)
            table3_totals_dict['SeventhPayNPS'] += (pay_diff_nps + nps + pay_diff)
            table3_totals_dict['Other'] += float(row.other or 0.0)

        table3_totals_dict['Expense_Total'] = sum(table3_totals_dict[k] for k in ['Medical', 'Festival', 'Swagram', 'SeventhPayNPS', 'Other'])

        table3_final_data_row = {
                "SrNo": 1,
                "Division": district,
                "Medical": int(round(table3_totals_dict['Medical'])),
                "Festival": int(round(table3_totals_dict['Festival'])),
                "Swagram": int(round(table3_totals_dict['Swagram'])),
                "SeventhPayNPS": int(round(table3_totals_dict['SeventhPayNPS'])),
                "Other": int(round(table3_totals_dict['Other'])),
                "Expense_Total": int(round(table3_totals_dict['Expense_Total']))
        }
        logger.info(f"(Helper REVISED v4.1) District expense totals: {table3_final_data_row}")

        return {
            "table1_rows": table1_rows,
            "table1_totals": dict(table1_totals),
            "table3_data": [table3_final_data_row]
        }
    
    except Exception as e:
        logger.error(f"(Helper REVISED v4.1) Error fetching/processing district post expenses summary data for {district}: {e}", exc_info=True)
        return None

@ttl_cache(ttl_seconds=180, use_global=True)
def get_district_post_expenses_charts_data(db: Session, district: str, fiscal_year: str) -> Dict[str, Any]:
    logger.info(f"Fetching district post expenses charts data for {district}")
    try:
        district_data = db.query(
            PostExpenses.district,
            func.sum(PostExpenses.filled_posts).label("total_filled"),
            func.sum(PostExpenses.vacant_posts).label("total_vacant"),
            func.sum(PostExpenses.medical_expenses).label("medical_exp"),
            func.sum(PostExpenses.festival_advance).label("festival_exp"),
            func.sum(PostExpenses.swagram_maharashtra_darshan).label("swagram_exp"),
            func.sum(PostExpenses.other).label("other_exp")
        ).filter(
            PostExpenses.district == district,
            PostExpenses.fiscal_year == fiscal_year
        ).group_by(PostExpenses.district).order_by(PostExpenses.district).all()
        
        class_district_data = db.query(
            PostExpenses.district,
            PostExpenses.class_type,
            func.sum(PostExpenses.filled_posts).label("filled"),
            func.sum(PostExpenses.vacant_posts).label("vacant")
        ).filter(
            PostExpenses.district == district,
            PostExpenses.fiscal_year == fiscal_year
        ).group_by(PostExpenses.district, PostExpenses.class_type).order_by(
            PostExpenses.district, PostExpenses.class_type).all()
        
        districts = []
        filled_posts, vacant_posts = [], []
        medical_exp, festival_exp, swagram_exp, other_exp = [], [], [], []
        
        for row in district_data:
            districts.append(row.district)
            filled_posts.append(int(row.total_filled or 0))
            vacant_posts.append(int(row.total_vacant or 0))
            medical_exp.append(int(row.medical_exp or 0))
            festival_exp.append(int(row.festival_exp or 0))
            swagram_exp.append(int(row.swagram_exp or 0))
            other_exp.append(int(row.other_exp or 0))
        
        class_data = defaultdict(lambda: defaultdict(int))
        for row in class_district_data:
            district_name = row.district
            class_type = row.class_type
            filled = int(row.filled or 0)
            vacant = int(row.vacant or 0)
            
            class_data[district_name][f'Class{class_type}_Filled'] = filled
            class_data[district_name][f'Class{class_type}_Vacant'] = vacant
            class_data[district_name][f'Class{class_type}_Total'] = filled + vacant
        
        district_class_breakdown = {}
        for dist in districts:
            district_class_breakdown[dist] = {
                '1': {
                    'filled': class_data[dist].get('Class1_Filled', 0),
                    'vacant': class_data[dist].get('Class1_Vacant', 0)
                },
                '2': {
                    'filled': class_data[dist].get('Class2_Filled', 0),
                    'vacant': class_data[dist].get('Class2_Vacant', 0)
                },
                '3': {
                    'filled': class_data[dist].get('Class3_Filled', 0),
                    'vacant': class_data[dist].get('Class3_Vacant', 0)
                },
                '4': {
                    'filled': class_data[dist].get('Class4_Filled', 0),
                    'vacant': class_data[dist].get('Class4_Vacant', 0)
                }
            }
        
        return {
            'scatter_posts': {
                'districts': districts,
                'filled': filled_posts,
                'vacant': vacant_posts
            },
            'pie_expenses': {
                'labels': ["Medical", "Festival", "Swagram", "Other"],
                'values': [
                    sum(medical_exp),
                    sum(festival_exp),
                    sum(swagram_exp),
                    sum(other_exp)
                ]
            },
            'stacked_classes': {
                'districts': districts,
                'class_data': district_class_breakdown
            },
            'polar_expenses': {
                'labels': districts,
                'medical': medical_exp,
                'other_combined': [festival_exp[i] + swagram_exp[i] + other_exp[i] for i in range(len(districts))]
            }
        }
    
    except Exception as e:
        logger.error(f"Error fetching district post expenses charts data for {district}: {e}", exc_info=True)
        return {}

@ttl_cache(ttl_seconds=180, use_global=True)
def get_post_expenses_summary_data(db: Session, fiscal_year: str = '2025-26') -> Dict[str, Any]:
    logger.info("--- (Helper REVISED v4.1) Fetching post expenses summary data (Tables 1 & 3 only) ---")
    try:
        post_counts_query = db.query(
            PostExpenses.class_type,
            PostExpenses.category,
            func.sum(PostExpenses.filled_posts).label("TotalFilled"),
            func.sum(PostExpenses.vacant_posts).label("TotalVacant")
        ).filter(
            PostExpenses.fiscal_year == fiscal_year,
            PostExpenses.district != DCO_STAFF_IDENTIFIER
        ).group_by(
            PostExpenses.class_type,
            PostExpenses.category
        ).all()
        logger.info(f"(Helper REVISED v4.1) Post counts query returned {len(post_counts_query)} rows.")

        expense_data_query = db.query(
            PostExpenses.district,
            PostExpenses.medical_expenses,
            PostExpenses.festival_advance,
            PostExpenses.swagram_maharashtra_darshan,
            PostExpenses.seventh_pay_commission_difference_nps,
            PostExpenses.nps,
            PostExpenses.seventh_pay_commission_difference,
            PostExpenses.other
        ).filter(
            PostExpenses.fiscal_year == fiscal_year,
            PostExpenses.district != DCO_STAFF_IDENTIFIER
        ).all()
        logger.info(f"(Helper REVISED v4.1) Base expense data query returned {len(expense_data_query)} rows for processing.")

        table1_data = defaultdict(lambda: defaultdict(int))
        for row in post_counts_query:
            cls = row.class_type
            cat = row.category
            if cls not in ['1', '2', '3', '4']: continue
            table1_data[cls][f"{cat}_Filled"] = int(row.TotalFilled or 0)
            table1_data[cls][f"{cat}_Vacant"] = int(row.TotalVacant or 0)

        table1_rows = []
        table1_totals = defaultdict(int)
        for i, cls in enumerate(['1', '2', '3', '4'], 1):
            row_data = {
                "SrNo": i,
                "Class": cls,
                "Permanent_Filled": table1_data[cls].get("Permanent_Filled", 0),
                "Permanent_Vacant": table1_data[cls].get("Permanent_Vacant", 0),
                "Temporary_Filled": table1_data[cls].get("Temporary_Filled", 0),
                "Temporary_Vacant": table1_data[cls].get("Temporary_Vacant", 0),
            }
            row_data["Row_Total"] = sum(row_data[k] for k in ["Permanent_Filled", "Permanent_Vacant", "Temporary_Filled", "Temporary_Vacant"])
            table1_rows.append(row_data)
            
            for key in ["Permanent_Filled", "Permanent_Vacant", "Temporary_Filled", "Temporary_Vacant", "Row_Total"]:
                table1_totals[key] += row_data[key]

        table1_totals["SrNo"] = "--"
        table1_totals["Class"] = "एकूण"

        table3_totals_dict = defaultdict(float)
        processed_districts = set()

        for row in expense_data_query:
            district = row.district
            if not district or district in processed_districts: continue
            
            processed_districts.add(district)
            table3_totals_dict['Medical'] += float(row.medical_expenses or 0.0)
            table3_totals_dict['Festival'] += float(row.festival_advance or 0.0)
            table3_totals_dict['Swagram'] += float(row.swagram_maharashtra_darshan or 0.0)
            pay_diff_nps = float(row.seventh_pay_commission_difference_nps or 0.0)
            nps = float(row.nps or 0.0)
            pay_diff = float(row.seventh_pay_commission_difference or 0.0)
            table3_totals_dict['SeventhPayNPS'] += (pay_diff_nps + nps + pay_diff)
            table3_totals_dict['Other'] += float(row.other or 0.0)

        table3_totals_dict['Expense_Total'] = sum(table3_totals_dict[k] for k in ['Medical', 'Festival', 'Swagram', 'SeventhPayNPS', 'Other'])

        table3_final_data_row = {
                "SrNo": 1,
                "Division": "कोकण विभाग",
                "Medical": int(round(table3_totals_dict['Medical'])),
                "Festival": int(round(table3_totals_dict['Festival'])),
                "Swagram": int(round(table3_totals_dict['Swagram'])),
                "SeventhPayNPS": int(round(table3_totals_dict['SeventhPayNPS'])),
                "Other": int(round(table3_totals_dict['Other'])),
                "Expense_Total": int(round(table3_totals_dict['Expense_Total']))
        }
        logger.info(f"(Helper REVISED v4.1) Processed expense totals: {table3_final_data_row}")

        return {
            "table1_rows": table1_rows,
            "table1_totals": dict(table1_totals),
            "table3_data": [table3_final_data_row]
        }
    
    except Exception as e:
        logger.error(f"(Helper REVISED v4.1) Error fetching/processing post expenses summary data: {e}", exc_info=True)
        return None

def get_post_expenses_charts_data(db: Session, fiscal_year: str = '2025-26') -> Dict[str, Any]:
    logger.info("Fetching post expenses charts data")
    try:
        district_data = db.query(
            PostExpenses.district,
            func.sum(PostExpenses.filled_posts).label("total_filled"),
            func.sum(PostExpenses.vacant_posts).label("total_vacant"),
            func.sum(PostExpenses.medical_expenses).label("medical_exp"),
            func.sum(PostExpenses.festival_advance).label("festival_exp"),
            func.sum(PostExpenses.swagram_maharashtra_darshan).label("swagram_exp"),
            func.sum(PostExpenses.other).label("other_exp")
        ).filter(
            PostExpenses.fiscal_year == fiscal_year,
            PostExpenses.district != DCO_STAFF_IDENTIFIER
        ).group_by(PostExpenses.district).order_by(PostExpenses.district).all()
        
        class_district_data = db.query(
            PostExpenses.district,
            PostExpenses.class_type,
            func.sum(PostExpenses.filled_posts).label("filled"),
            func.sum(PostExpenses.vacant_posts).label("vacant")
        ).filter(
            PostExpenses.fiscal_year == fiscal_year,
            PostExpenses.district != DCO_STAFF_IDENTIFIER
        ).group_by(PostExpenses.district, PostExpenses.class_type).order_by(
            PostExpenses.district, PostExpenses.class_type).all()
        
        districts = []
        filled_posts, vacant_posts = [], []
        medical_exp, festival_exp, swagram_exp, other_exp = [], [], [], []
        
        for row in district_data:
            districts.append(row.district or 'Unknown')
            filled_posts.append(int(row.total_filled or 0))
            vacant_posts.append(int(row.total_vacant or 0))
            medical_exp.append(int(row.medical_exp or 0))
            festival_exp.append(int(row.festival_exp or 0))
            swagram_exp.append(int(row.swagram_exp or 0))
            other_exp.append(int(row.other_exp or 0))
        
        class_data = {}
        for row in class_district_data:
            district = row.district or 'Unknown'
            class_type = row.class_type or 'Unknown'
            if district not in class_data:
                class_data[district] = {}
            class_data[district][class_type] = {
                'filled': int(row.filled or 0),
                'vacant': int(row.vacant or 0)
            }
        
        expense_totals = []
        for i, district in enumerate(districts):
            total_expense = medical_exp[i] + festival_exp[i] + swagram_exp[i] + other_exp[i]
            expense_totals.append(total_expense)
        
        chart_data = {
            "scatter_posts": {
                "districts": districts,
                "filled": filled_posts,
                "vacant": vacant_posts
            },
            "pie_expenses": {
                "labels": ["Medical", "Festival", "Swagram", "Other"],
                "values": [
                    sum(medical_exp),
                    sum(festival_exp), 
                    sum(swagram_exp),
                    sum(other_exp)
                ]
            },
            "stacked_classes": {
                "districts": districts,
                "class_data": class_data
            },
            "polar_expenses": {
                "labels": districts,
                "medical": medical_exp,
                "other_combined": [festival_exp[i] + swagram_exp[i] + other_exp[i] for i in range(len(districts))]
            }
        }
        
        logger.info(f"Generated post expenses charts data for {len(districts)} districts")
        return chart_data
        
    except Exception as e:
        logger.error(f"Error generating post expenses charts data: {e}", exc_info=True)
        return {}

@router.get("", response_class=HTMLResponse)
async def ui_list_post_expenses(
    request: Request, db: Session = Depends(get_db), view: Optional[str] = Query("edit"),
    district: Optional[str] = Query(None), category: Optional[str] = Query(None),
    cls: Optional[str] = Query(None, alias="class"),
    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=500)
):
    auth_role = request.cookies.get('auth_role', '')
    auth_level = request.cookies.get('auth_level', '')
    auth_unit = request.cookies.get('auth_unit', '')
    can_edit = check_edit_permission(auth_role, auth_level, auth_unit, db)
    if auth_level == 'district' and auth_unit:
        districts_for_filter = [auth_unit]
    elif auth_level == 'dco':
        districts_for_filter = DISTRICTS
    else:
        districts_for_filter = REGULAR_DISTRICTS
    
    context = {
        "request": request, "resource_name": "प्रपत्र ब", "districts": districts_for_filter,
        "categories": CATEGORIES, "classes": CLASSES_SHEET3, "current_district": district,
        "current_category": category, "current_class": cls, "view_mode": view,
        "districts_mr": DISTRICTS_MR, "categories_mr": CATEGORIES_MR, "classes_sheet3_mr": CLASSES_SHEET3_MR,
        "auth_level": auth_level, "auth_unit": auth_unit
    }

    if view == "summary":
        fiscal_year = get_fiscal_year_from_request(request, db)
        if auth_level == 'district' and auth_unit:
            summary_data = get_district_post_expenses_summary_data(db, auth_unit, fiscal_year)
            charts_data = get_district_post_expenses_charts_data(db, auth_unit, fiscal_year)
        elif auth_level == 'taluka' and auth_unit:
            district_name = get_district_from_taluka(auth_unit)
            if district_name:
                summary_data = get_district_post_expenses_summary_data(db, district_name, fiscal_year)
                charts_data = get_district_post_expenses_charts_data(db, district_name, fiscal_year)
            else:
                summary_data = None
                charts_data = {}
        else:
            summary_data = get_post_expenses_summary_data(db, fiscal_year)
            charts_data = get_post_expenses_charts_data(db, fiscal_year)
        
        if not summary_data:
            raise HTTPException(status_code=500, detail="Could not generate Post Expenses summary data.")
        context.update({"resource_name": "प्रपत्र ब गोषवारा", "chart_data_json": json.dumps(charts_data)})
        context.update(summary_data)
        response = templates.TemplateResponse("schemes/s2053/subs/s20530028/post_expenses_list.html", context)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    elif view == "edit":
        fiscal_year = get_fiscal_year_from_request(request, db)
        _, sub_scheme = get_scheme_from_cookies(request)
        query = build_district_filter(db.query(PostExpenses), auth_level, auth_unit, PostExpenses).filter(
            PostExpenses.fiscal_year == fiscal_year,
            PostExpenses.sub_scheme_code == sub_scheme
        )
        
        if district:
            query = query.filter(PostExpenses.district == district)
        if category:
            query = query.filter(PostExpenses.category == category)
        if cls:
            query = query.filter(PostExpenses.class_type == cls)
        
        total_count = query.with_entities(func.count()).scalar()
        items = query.order_by(PostExpenses.id).offset((page - 1) * page_size).limit(page_size).all()
        
        filtered_params = {k: v for k, v in {"district": district, "category": category, "class": cls}.items() if v}
        context.update({
            "export_query_string_list": "?" + urlencode(filtered_params) if filtered_params else "",
            "items": items, "total_count": total_count, "page": page,
            "page_size": page_size, "can_edit": can_edit
        })
        response = templates.TemplateResponse("schemes/s2053/subs/s20530028/post_expenses_list.html", context)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    
    else:
        raise HTTPException(status_code=400, detail="Invalid view parameter. Use 'edit' or 'summary'.")


@router.get("/{id}/edit", response_class=HTMLResponse)
async def ui_edit_post_expense_form(request: Request, id: int, db: Session = Depends(get_db)):
    from src.utils_timing import check_data_filling_allowed
    auth_level = request.cookies.get('auth_level')
    auth_role = request.cookies.get('auth_role')
    auth_unit = request.cookies.get('auth_unit')
    
    is_allowed, timing_msg = check_data_filling_allowed(db, auth_level, auth_role)
    if not is_allowed and auth_role == 'assistant':
        raise HTTPException(status_code=403, detail=timing_msg or "Data filling period has expired")
    
    if auth_level == 'district' and auth_unit:
        districts_for_filter = [auth_unit]
    elif auth_level == 'dco':
        districts_for_filter = DISTRICTS
    else:
        districts_for_filter = REGULAR_DISTRICTS
    
    item = db.query(PostExpenses).filter(PostExpenses.id == id).first()
    if not item: raise HTTPException(status_code=404, detail=f"प्रपत्र ब ID {id} सापडला नाही")
    active_component = POST_EXPENSES_DISTRICT_COMPONENT_FIELD.get(item.district if item else None)
    return templates.TemplateResponse("schemes/s2053/subs/s20530028/post_expenses_form.html", {
        "request": request, "districts": districts_for_filter, "categories": CATEGORIES,
        "classes": CLASSES_SHEET3, "item": item, "resource_name": "प्रपत्र ब संपादन",
        "districts_mr": DISTRICTS_MR, "categories_mr": CATEGORIES_MR, "classes_sheet3_mr": CLASSES_SHEET3_MR,
        "active_component": active_component, "auth_level": auth_level
    })


@router.post("/{id}/edit", response_class=RedirectResponse)
async def ui_update_post_expense(
    request: Request, id: int, db: Session = Depends(get_db),
    Class: str = Form(...), Category: str = Form(...), District: str = Form(...),
    FilledPosts: Optional[int] = Form(None), VacantPosts: Optional[int] = Form(None),
    MedicalExpenses: Optional[int] = Form(None), FestivalAdvance: Optional[int] = Form(None),
    SwagramMaharashtraDarshan: Optional[int] = Form(None), Other: Optional[int] = Form(None),
    SeventhPayCommissionDifferenceNPS: Optional[str] = Form(None),
    NPS: Optional[str] = Form(None),
    SeventhPayCommissionDifference: Optional[str] = Form(None),
):
    from src.utils_timing import check_data_filling_allowed
    auth_role = request.cookies.get('auth_role') or ''
    auth_level = request.cookies.get('auth_level') or ''
    auth_unit = request.cookies.get('auth_unit') or ''
    if auth_role in ("officer1","officer2","dco"):
        raise HTTPException(status_code=403, detail="Forbidden")
    if auth_level == 'taluka' and auth_unit:
        if not is_taluka_allowed(db, auth_unit):
            raise HTTPException(status_code=403, detail="Taluka not allowed")
        if District != get_district_from_taluka_name(auth_unit):
            raise HTTPException(status_code=400, detail="Invalid district for taluka user")
    
    is_allowed, timing_msg = check_data_filling_allowed(db, auth_level, auth_role)
    if not is_allowed:
        raise HTTPException(status_code=403, detail=timing_msg or "Data filling period has expired")
    
    db_item = db.query(PostExpenses).filter(PostExpenses.id == id).first()
    if not db_item: raise HTTPException(status_code=404, detail=f"प्रपत्र ब ID {id} सापडला नाही")

    def safe_float(value: Optional[str]) -> Optional[float]:
        if value is None or value.strip() == "":
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            raise ValueError(f"Invalid number format: '{value}'")

    form_data = {
        "Class": Class, "Category": Category, "District": District, "FilledPosts": FilledPosts,
        "VacantPosts": VacantPosts, "MedicalExpenses": MedicalExpenses, "FestivalAdvance": FestivalAdvance,
        "SwagramMaharashtraDarshan": SwagramMaharashtraDarshan, "Other": Other
    }

    try:
        form_data["SeventhPayCommissionDifferenceNPS"] = safe_float(SeventhPayCommissionDifferenceNPS)
        form_data["NPS"] = safe_float(NPS)
        form_data["SeventhPayCommissionDifference"] = safe_float(SeventhPayCommissionDifference)

        mapping = {
            "Class": "class_type", "Category": "category", "District": "district",
            "FilledPosts": "filled_posts", "VacantPosts": "vacant_posts",
            "MedicalExpenses": "medical_expenses", "FestivalAdvance": "festival_advance",
            "SwagramMaharashtraDarshan": "swagram_maharashtra_darshan", "Other": "other",
            "SeventhPayCommissionDifferenceNPS": "seventh_pay_commission_difference_nps",
            "NPS": "nps", "SeventhPayCommissionDifference": "seventh_pay_commission_difference"
        }
        for key, value in form_data.items():
            model_field = mapping.get(key)
            if model_field and hasattr(db_item, model_field):
                setattr(db_item, model_field, value)

        active_component = POST_EXPENSES_DISTRICT_COMPONENT_FIELD.get(District)
        sync_candidates = {
            "medical_expenses": form_data.get("MedicalExpenses"),
            "festival_advance": form_data.get("FestivalAdvance"),
            "swagram_maharashtra_darshan": form_data.get("SwagramMaharashtraDarshan"),
            "other": form_data.get("Other"),
        }
        if active_component == 'SeventhPayCommissionDifferenceNPS':
            sync_candidates["seventh_pay_commission_difference_nps"] = form_data.get("SeventhPayCommissionDifferenceNPS")
            sync_candidates["nps"] = None
            sync_candidates["seventh_pay_commission_difference"] = None
        elif active_component == 'NPS':
            sync_candidates["nps"] = form_data.get("NPS")
            sync_candidates["seventh_pay_commission_difference_nps"] = None
            sync_candidates["seventh_pay_commission_difference"] = None
        elif active_component == 'SeventhPayCommissionDifference':
            sync_candidates["seventh_pay_commission_difference"] = form_data.get("SeventhPayCommissionDifference")
            sync_candidates["seventh_pay_commission_difference_nps"] = None
            sync_candidates["nps"] = None
        sync_update = {k: v for k, v in sync_candidates.items() if v is not None}
        if sync_update:
            db.query(PostExpenses).filter(
                PostExpenses.district == District,
                PostExpenses.fiscal_year == db_item.fiscal_year
            ).update(sync_update, synchronize_session=False)
        db.commit(); db.refresh(db_item)
        logger.info(f"Successfully updated Post Expense ID {id}")
        return RedirectResponse(url=router.url_path_for("ui_list_post_expenses") + "?view=edit", status_code=status.HTTP_303_SEE_OTHER)

    except ValueError as ve:
        db.rollback()
        logger.error(f"Invalid float input during update for Post Expense ID {id}: {ve}")
        db_item_reloaded = db.query(PostExpenses).filter(PostExpenses.id == id).first()
        active_component = POST_EXPENSES_DISTRICT_COMPONENT_FIELD.get(db_item_reloaded.district if db_item_reloaded else None)
        districts_for_filter = DISTRICTS
        if auth_level == 'district' and auth_unit:
            districts_for_filter = [auth_unit]
        return templates.TemplateResponse("schemes/s2053/subs/s20530028/post_expenses_form.html", {
            "request": request, "error": f"Failed to update: {ve}",
            "districts": districts_for_filter, "categories": CATEGORIES, "classes": CLASSES_SHEET3,
            "item": db_item_reloaded, "resource_name": "प्रपत्र ब संपादन", "active_component": active_component,
            "districts_mr": DISTRICTS_MR, "categories_mr": CATEGORIES_MR, "classes_sheet3_mr": CLASSES_SHEET3_MR,
            "auth_level": auth_level
        }, status_code=400)

    except Exception as e:
        db.rollback(); logger.error(f"Failed to update Post Expense ID {id}: {e}", exc_info=True)
        db_item_reloaded = db.query(PostExpenses).filter(PostExpenses.id == id).first()
        active_component = POST_EXPENSES_DISTRICT_COMPONENT_FIELD.get(db_item_reloaded.district if db_item_reloaded else None)
        if auth_level == 'district' and auth_unit:
            districts_for_filter = [auth_unit]
        elif auth_level == 'dco':
            districts_for_filter = DISTRICTS
        else:
            districts_for_filter = REGULAR_DISTRICTS
        return templates.TemplateResponse("schemes/s2053/subs/s20530028/post_expenses_form.html", {
            "request": request, "error": f"Failed to update record: {e}",
            "districts": districts_for_filter, "categories": CATEGORIES, "classes": CLASSES_SHEET3,
            "item": db_item_reloaded, "resource_name": "प्रपत्र ब संपादन", "active_component": active_component,
            "districts_mr": DISTRICTS_MR, "categories_mr": CATEGORIES_MR, "classes_sheet3_mr": CLASSES_SHEET3_MR,
            "auth_level": auth_level
        }, status_code=500)


@router.get("/summary/export-excel", response_class=StreamingResponse)
async def export_post_expenses_summary_excel(request: Request, db: Session = Depends(get_db)):
    import pandas as pd
    import io
    
    logger.info("--- Entered export_post_expenses_summary_excel (Revised) ---")
    fiscal_year = get_fiscal_year_from_request(request, db)
    summary_data = get_post_expenses_summary_data(db, fiscal_year)
    if summary_data is None: raise HTTPException(status_code=500, detail="Could not generate summary data for download.")
    try:
        logger.info("Preparing data for Post Expenses Summary Excel (Tables 1 & 3)...")
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df1_rows = pd.DataFrame(summary_data['table1_rows']); df1_totals = pd.DataFrame([summary_data['table1_totals']]); df1 = pd.concat([df1_rows, df1_totals], ignore_index=True)
            df1.columns = ["अ.क्र.", "वर्ग", "स्थायी-भरलेली", "स्थायी-रिक्त", "अस्थायी-भरलेली", "अस्थायी-रिक्त", "एकूण पदे"]
            df1.to_excel(writer, sheet_name='Post Counts by Class', index=False)
            df3 = pd.DataFrame(summary_data['table3_data'])
            df3 = df3[['SrNo', 'Division', 'Medical', 'Festival', 'Swagram', 'SeventhPayNPS', 'Other', 'Expense_Total']]
            df3.columns = ["अ.क्र.", "जिल्हा / विभाग", "वैद्यकिय खर्च", "उत्सव/सण अग्रिम", "स्वग्राम/महाराष्ट्र दर्शन", "7 व्या वेतन आयोग फरक+ NPS", "इतर", "एकूण खर्च"]
            df3.to_excel(writer, sheet_name='Expense Summary', index=False)
        output.seek(0)
        logger.info("Post Expenses Summary Excel file created, preparing response...")
        headers = {'Content-Disposition': 'attachment; filename="post_expenses_summary_report.xlsx"'}
        return StreamingResponse(output, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    except Exception as e:
        logger.error(f"Failed to generate Post Expenses Summary Excel file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Could not generate Excel file: {e}")

@router.get("/list/export-excel", response_class=StreamingResponse)
async def export_post_expenses_list_excel(
    request: Request,
    db: Session = Depends(get_db),
    district: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    cls: Optional[str] = Query(None, alias="class")
):
    import pandas as pd
    import io
    
    logger.info("--- Entered export_post_expenses_LIST_excel ---")
    fiscal_year = get_fiscal_year_from_request(request, db)
    query = db.query(PostExpenses).filter(PostExpenses.fiscal_year == fiscal_year)
    if district: query = query.filter(PostExpenses.district == district)
    if category: query = query.filter(PostExpenses.category == category)
    if cls: query = query.filter(PostExpenses.class_type == cls)
    items = query.order_by(PostExpenses.id).all()
    data_dict_list = []
    if items:
        columns = [c.name for c in PostExpenses.__table__.columns]
        for item in items: data_dict_list.append({col: getattr(item, col, None) for col in columns})
    df = pd.DataFrame(data_dict_list)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Post Expenses List', index=False)
    output.seek(0)
    headers = {'Content-Disposition': 'attachment; filename="post_expenses_list.xlsx"'}
    return StreamingResponse(output, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@router.get("/export-original", response_class=StreamingResponse)
async def export_post_expenses_original(request: Request, db: Session = Depends(get_db), district: Optional[str] = Query(None)):
    auth_level = request.cookies.get('auth_level')
    auth_unit = request.cookies.get('auth_unit')
    user_district = None
    if auth_level == 'district':
        user_district = auth_unit
    elif auth_level in ('dco', 'officer1', 'officer2') and district:
        user_district = district
    return export_original_workbook(db, user_district=user_district)

@router.get("/export-sheet-only", response_class=StreamingResponse)
async def export_post_expenses_sheet_only(request: Request, db: Session = Depends(get_db), district: Optional[str] = Query(None)):
    auth_level = request.cookies.get('auth_level')
    auth_unit = request.cookies.get('auth_unit')
    user_district = None
    if auth_level == 'district':
        user_district = auth_unit
    elif auth_level in ('dco', 'officer1', 'officer2') and district:
        user_district = district
    return export_original_workbook(db, only_sheet="post_expenses", user_district=user_district)