from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.responses import HTMLResponse
from starlette.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from typing import Dict, Any, Optional
from collections import defaultdict
import logging

from src.database import get_db
from src.core.templates import render
from src.utils_cache import ttl_cache
from src.utils_auth import get_auth_level
from src.config import DCO_STAFF_IDENTIFIER
from src.utils_fiscal_year import get_default_fiscal_year, get_fiscal_year_from_request, get_relative_fiscal_years
from src.utils_da_rate import get_da_rate
from .models import BudgetPostDetails
from .config import POSITION_ORDER, CLASS_1_2_KEY, CLASS_3_KEY, CLASS_4_KEY, VALID_CLASS_KEYS, HRA_RATE_MAP
from .helpers import get_no_cache_headers

POSITION_SORT_MAP = {name: i for i, name in enumerate(POSITION_ORDER)}
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ui/s20290037/budget-summary",
    tags=["UI - Budget Summary"],
    include_in_schema=False
)

CLASS_LABEL_MAP_MR = {
    CLASS_1_2_KEY: 'वर्ग-1 व 2',
    CLASS_3_KEY: 'वर्ग-3',
    CLASS_4_KEY: 'वर्ग-4'
}
CATEGORY_LABEL_MAP_MR = {
    'Permanent': 'स्थायी',
    'Temporary': 'अस्थायी'
}
TOTAL_CLASS_LABEL_MR = "वर्ग-1,2,3 व 4"
GRAND_TOTAL_CATEGORY_LABEL_MR = "स्थायी + अस्थायी"

def _process_budget_query_results(query_results, internal_col_keys, da_rate: float, include_dearness: bool = True, include_hra: bool = True):
    """Process budget query results to generate detailed rows and totals"""
    permanent_rows_unsorted = []
    temporary_rows_unsorted = []
    permanent_totals_detailed = defaultdict(int)
    temporary_totals_detailed = defaultdict(int)
    class_summary_agg = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    
    for key in internal_col_keys:
        permanent_totals_detailed[key] = 0
        temporary_totals_detailed[key] = 0

    
    for i, row in enumerate(query_results):
        raw_class_value = (getattr(row, 'class_type', '') or "").strip()
        current_class_key = None
        if raw_class_value == CLASS_1_2_KEY: 
            current_class_key = CLASS_1_2_KEY
        elif raw_class_value == CLASS_3_KEY: 
            current_class_key = CLASS_3_KEY
        elif raw_class_value == CLASS_4_KEY: 
            current_class_key = CLASS_4_KEY
        else:
            logger.warning(f"Row {i}: Unexpected class value '{raw_class_value}'. Skipping.")
            continue

        special_pay = int(row.Sum_SpecialPay or 0)
        basic_pay_raw = float(row.Sum_BasicPay or 0)
        basic_pay = int(basic_pay_raw * 1000 if basic_pay_raw < 1000 else basic_pay_raw)
        grade_pay = int(row.Sum_GradePay or 0)
        total_pay = special_pay + basic_pay + grade_pay
        local_supp_allowance = int(row.Sum_LocalSupplemetoryAllowance or 0)
        base_for_allowances = basic_pay + grade_pay
        dearness_allowance = round(base_for_allowances * da_rate) if include_dearness else 0
        hra = round(float(row.Sum_Hra or 0)) if include_hra else 0
        vehicle_allowance = int(row.Sum_VehicleAllowance or 0)
        washing_allowance = int(row.Sum_WashingAllowance or 0)
        cash_allowance = int(row.Sum_CashAllowance or 0)
        footwear_others = int(row.Sum_FootWareAllowanceOther or 0)
        grand_total = (total_pay + dearness_allowance + local_supp_allowance + hra +
                      vehicle_allowance + washing_allowance + cash_allowance + footwear_others)

        processed_row = {
            "Class": raw_class_value,
            "Position": getattr(row, 'designation', ''),
            "Approved Posts Prev1": int(row.Sum_SanctionedPrev1 or 0),
            "Approved Posts Curr": int(row.Sum_SanctionedCurr or 0),
            "Special Pay": special_pay,
            "Basic Pay": basic_pay,
            "Grade Pay": grade_pay,
            "Total Pay": total_pay,
            "Dearness Allowance 64%": dearness_allowance,
            "Local Supplementary Allowance": local_supp_allowance,
            "House Rent Allowance": hra,
            "Vehicle Allowance": vehicle_allowance,
            "Washing Allowance": washing_allowance,
            "Cash Allowance": cash_allowance,
            "Footwear Allowance / Others": footwear_others,
            "Total": grand_total
        }

        target_agg_dict = class_summary_agg[getattr(row, 'category', None)][current_class_key]
        for key in internal_col_keys:
            target_agg_dict[key] += processed_row.get(key, 0)

        if getattr(row, 'category', None) == 'Permanent':
            permanent_rows_unsorted.append(processed_row)
            for key in internal_col_keys: 
                permanent_totals_detailed[key] += processed_row.get(key, 0)
        elif getattr(row, 'category', None) == 'Temporary':
            temporary_rows_unsorted.append(processed_row)
            for key in internal_col_keys: 
                temporary_totals_detailed[key] += processed_row.get(key, 0)

    def sort_key(row_dict):
        position = row_dict.get('Position')
        return POSITION_SORT_MAP.get(position, float('inf')) if position else float('inf')

    permanent_rows_sorted = sorted(permanent_rows_unsorted, key=sort_key)
    temporary_rows_sorted = sorted(temporary_rows_unsorted, key=sort_key)

    permanent_rows_final = [{"Sr No.": i, **row} for i, row in enumerate(permanent_rows_sorted, 1)]
    temporary_rows_final = [{"Sr No.": i, **row} for i, row in enumerate(temporary_rows_sorted, 1)]

    permanent_totals_render = {"Sr No.": "--", "Position": "एकूण", **permanent_totals_detailed}
    temporary_totals_render = {"Sr No.": "--", "Position": "एकूण", **temporary_totals_detailed}

    final_summary_rows = []
    grand_totals_summary = defaultdict(int)

    for category_internal in ['Permanent', 'Temporary']:
        category_label_mr = CATEGORY_LABEL_MAP_MR.get(category_internal, category_internal)
        category_total_summary = {
            "CategoryLabel": category_label_mr,
            "ClassLabel": TOTAL_CLASS_LABEL_MR
        }

        for cls_key_internal in VALID_CLASS_KEYS:
            cls_label_mr = CLASS_LABEL_MAP_MR.get(cls_key_internal, cls_key_internal)
            aggregated_data = class_summary_agg[category_internal].get(cls_key_internal, defaultdict(int))
            output_row = {
                "CategoryLabel": category_label_mr,
                "ClassLabel": cls_label_mr
            }
            for key in internal_col_keys:
                output_row[key] = aggregated_data.get(key, 0)
            final_summary_rows.append(output_row)

        current_category_totals = permanent_totals_detailed if category_internal == 'Permanent' else temporary_totals_detailed
        for key in internal_col_keys:
            value = current_category_totals.get(key, 0)
            category_total_summary[key] = value
            grand_totals_summary[key] += value

        final_summary_rows.append(category_total_summary)

    grand_total_row = {"CategoryLabel": GRAND_TOTAL_CATEGORY_LABEL_MR, "ClassLabel": ""}
    for key in internal_col_keys:
        grand_total_row[key] = grand_totals_summary.get(key, 0)
    final_summary_rows.append(grand_total_row)
    
    return {
        "permanent_rows": permanent_rows_final,
        "temporary_rows": temporary_rows_final,
        "permanent_totals_render": permanent_totals_render,
        "temporary_totals_render": temporary_totals_render,
        "final_summary_rows": final_summary_rows,
        "class_summary_agg": class_summary_agg,
        "permanent_totals_detailed": permanent_totals_detailed,
        "temporary_totals_detailed": temporary_totals_detailed
    }

@ttl_cache(ttl_seconds=180, use_global=True)
def get_budget_summary_data(db: Session, fiscal_year: Optional[str] = None, district: Optional[str] = None) -> Dict[str, Any]:
    """Unified function for both district and overall budget summary data"""
    if not fiscal_year:
        fiscal_year = get_default_fiscal_year(db)
    
    try:
        da_rate = get_da_rate(db, fiscal_year)
        hra_calc = (BudgetPostDetails.basic_pay + BudgetPostDetails.grade_pay) * case(
            (BudgetPostDetails.hra_rate == 'X', HRA_RATE_MAP['X']),
            (BudgetPostDetails.hra_rate == 'Y', HRA_RATE_MAP['Y']),
            (BudgetPostDetails.hra_rate == 'Z', HRA_RATE_MAP['Z']),
            else_=HRA_RATE_MAP['X']
        )
        
        query = db.query(
            BudgetPostDetails.category,
            BudgetPostDetails.class_type,
            BudgetPostDetails.designation,
            func.sum(BudgetPostDetails.sanctioned_posts_prev1).label("Sum_SanctionedPrev1"),
            func.sum(BudgetPostDetails.sanctioned_posts_curr).label("Sum_SanctionedCurr"),
            func.sum(BudgetPostDetails.special_pay).label("Sum_SpecialPay"),
            func.sum(BudgetPostDetails.basic_pay).label("Sum_BasicPay"),
            func.sum(BudgetPostDetails.grade_pay).label("Sum_GradePay"),
            func.sum(BudgetPostDetails.local_supplementary_allowance).label("Sum_LocalSupplemetoryAllowance"),
            func.sum(hra_calc).label("Sum_Hra"),
            func.sum(BudgetPostDetails.vehicle_allowance).label("Sum_VehicleAllowance"),
            func.sum(BudgetPostDetails.washing_allowance).label("Sum_WashingAllowance"),
            func.sum(BudgetPostDetails.cash_allowance).label("Sum_CashAllowance"),
            func.sum(BudgetPostDetails.footwear_allowance_other).label("Sum_FootWareAllowanceOther")
        ).filter(BudgetPostDetails.fiscal_year == fiscal_year)
        
        if district:
            query = query.filter(BudgetPostDetails.district == district)
        else:
            query = query.filter(BudgetPostDetails.district != DCO_STAFF_IDENTIFIER)
        
        query = query.group_by(
            BudgetPostDetails.category,
            BudgetPostDetails.class_type,
            BudgetPostDetails.designation
        ).order_by(BudgetPostDetails.category)
        
        query_results = query.all()
        
        internal_col_keys = [
            "Approved Posts Prev1", "Approved Posts Curr", "Special Pay", "Basic Pay", "Grade Pay",
            "Total Pay", "Dearness Allowance 64%", "Local Supplementary Allowance", "House Rent Allowance",
            "Vehicle Allowance", "Washing Allowance", "Cash Allowance", "Footwear Allowance / Others", "Total"
        ]
        
        include_dearness = bool(district)
        include_hra = bool(district)
        
        processed_data = _process_budget_query_results(query_results, internal_col_keys, da_rate, include_dearness, include_hra)

        district_records = db.query(
            BudgetPostDetails.district,
            BudgetPostDetails.category,
            func.sum(BudgetPostDetails.sanctioned_posts_curr).label("Sum_SanctionedCurr"),
            func.sum(BudgetPostDetails.special_pay).label("Sum_SpecialPay"),
            func.sum(BudgetPostDetails.basic_pay).label("Sum_BasicPay"),
            func.sum(BudgetPostDetails.grade_pay).label("Sum_GradePay"),
            func.sum(BudgetPostDetails.local_supplementary_allowance).label("Sum_LocalSupplemetoryAllowance"),
            func.sum(hra_calc).label("Sum_Hra"),
            func.sum(BudgetPostDetails.vehicle_allowance).label("Sum_VehicleAllowance"),
            func.sum(BudgetPostDetails.washing_allowance).label("Sum_WashingAllowance"),
            func.sum(BudgetPostDetails.cash_allowance).label("Sum_CashAllowance"),
            func.sum(BudgetPostDetails.footwear_allowance_other).label("Sum_FootWareAllowanceOther")
        ).filter(
            BudgetPostDetails.fiscal_year == fiscal_year,
            BudgetPostDetails.district != DCO_STAFF_IDENTIFIER
        ).group_by(
            BudgetPostDetails.district,
            BudgetPostDetails.category
        ).all()
        
        district_summary = defaultdict(lambda: {"Permanent": {"PostsCurr": 0, "TotalCost": 0}, "Temporary": {"PostsCurr": 0, "TotalCost": 0}})
        district_components = defaultdict(lambda: {"Special": 0, "Basic": 0, "Grade": 0, "Allowances": 0})
        district_totals_for_scatter = defaultdict(lambda: {"Posts": 0, "Cost": 0, "Grade": 0})
        
        for r in district_records:
            d = getattr(r, 'district', None) or ''
            c = getattr(r, 'category', None) or ''
            if d and c in ('Permanent', 'Temporary'):
                posts_curr = int(getattr(r, 'Sum_SanctionedCurr', 0) or 0)
                sp = int(getattr(r, 'Sum_SpecialPay', 0) or 0)
                bp_raw = float(getattr(r, 'Sum_BasicPay', 0) or 0)
                bp = int(bp_raw * 1000 if bp_raw < 1000 else bp_raw)
                gp = int(getattr(r, 'Sum_GradePay', 0) or 0)
                lsa = int(getattr(r, 'Sum_LocalSupplemetoryAllowance', 0) or 0)
                hra = round(float(getattr(r, 'Sum_Hra', 0) or 0))
                va = int(getattr(r, 'Sum_VehicleAllowance', 0) or 0)
                wa = int(getattr(r, 'Sum_WashingAllowance', 0) or 0)
                ca = int(getattr(r, 'Sum_CashAllowance', 0) or 0)
                fo = int(getattr(r, 'Sum_FootWareAllowanceOther', 0) or 0)
                total_cost = sp + bp + gp + lsa + hra + va + wa + ca + fo
                district_summary[d][c]["PostsCurr"] += posts_curr
                district_summary[d][c]["TotalCost"] += total_cost
                district_components[d]["Special"] += sp
                district_components[d]["Basic"] += bp
                district_components[d]["Grade"] += gp
                district_components[d]["Allowances"] += (lsa + hra + va + wa + ca + fo)
                district_totals_for_scatter[d]["Posts"] += posts_curr
                district_totals_for_scatter[d]["Cost"] += total_cost
                district_totals_for_scatter[d]["Grade"] += gp
        
        result = {
            **processed_data,
            "internal_col_keys_for_template": internal_col_keys,
            "district_summary": district_summary,
            "district_components": district_components,
            "district_totals_for_scatter": district_totals_for_scatter
        }
        del result['class_summary_agg']
        del result['permanent_totals_detailed']
        del result['temporary_totals_detailed']
        return result

    except Exception as e:
        logger.error(f"Error during budget summary data processing (district={district}): {e}", exc_info=True)
        return None

# Backward compatibility wrappers
def get_district_budget_summary_data(db: Session, district: str, fiscal_year: Optional[str] = None) -> Dict[str, Any]:
    return get_budget_summary_data(db, fiscal_year, district=district)



@router.get("", response_class=HTMLResponse)
async def ui_budget_summary_report(request: Request, db: Session = Depends(get_db)):
    fiscal_year = get_fiscal_year_from_request(request, db)
    summary_data = get_budget_summary_data(db, fiscal_year)

    if not summary_data:
        raise HTTPException(status_code=500, detail="Could not generate summary data.")

    try:
        auth_level = get_auth_level(request)
        da_rate = get_da_rate(db, fiscal_year)
        template_context = {
            "request": request,
            "resource_name": "अर्थसंकल्पीय अंदाजपत्रक सारांश",
            "view_mode": "summary",
            "chart_data": {},
            "auth_level": auth_level,
            "da_rate": da_rate,
            "relative_years": get_relative_fiscal_years(fiscal_year),
            **summary_data
        }
        response = render(request, "schemes/s2029/subs/s20290037/budget_post_details_list.html", template_context)
        response.headers.update(get_no_cache_headers())
        return response
    except Exception as e:
         logger.error(f"Error during HTML template rendering: {e}", exc_info=True)
         raise HTTPException(status_code=500, detail=f"Template rendering error: {e}")


@router.get("/download", response_class=StreamingResponse)
async def download_budget_summary_excel(request: Request, db: Session = Depends(get_db)):
    import pandas as pd
    import io
    
    fiscal_year = get_fiscal_year_from_request(request, db)
    summary_data = get_budget_summary_data(db, fiscal_year)

    if not summary_data:
        raise HTTPException(status_code=500, detail="Could not generate summary data for download.")

    try:
        perm_df = pd.DataFrame(summary_data["permanent_rows"])
        temp_df = pd.DataFrame(summary_data["temporary_rows"])
        final_summary_data_for_df = []
        for row in summary_data["final_summary_rows"]:
            df_row = {
                "Category": row.get("CategoryLabel"),
                "Class": row.get("ClassLabel"),
                **{key: row.get(key, 0) for key in summary_data.get("internal_col_keys_for_template", [])}
            }
            final_summary_data_for_df.append(df_row)
        summary_df = pd.DataFrame(final_summary_data_for_df)


        excel_col_order_detail = [
             "Sr No.", "Class", "Position", "Approved Posts Prev1", "Approved Posts Curr",
             "Special Pay", "Basic Pay", "Grade Pay", "Total Pay", "Dearness Allowance 64%",
             "Local Supplementary Allowance", "House Rent Allowance", "Vehicle Allowance",
             "Washing Allowance", "Cash Allowance", "Footwear Allowance / Others", "Total"
        ]

        excel_col_order_summary = ["Category", "Class"] + summary_data.get("internal_col_keys_for_template", [])


        if not perm_df.empty:
             cols_to_use = [col for col in excel_col_order_detail if col in perm_df.columns]
             perm_df = perm_df[cols_to_use]
        if not temp_df.empty:
             cols_to_use = [col for col in excel_col_order_detail if col in temp_df.columns]
             temp_df = temp_df[cols_to_use]
        if not summary_df.empty:
             cols_to_use = [col for col in excel_col_order_summary if col in summary_df.columns]
             summary_df = summary_df[cols_to_use]


        logger.info("Creating Excel file in memory...")
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            perm_df.to_excel(writer, sheet_name='Permanent Posts', index=False)
            temp_df.to_excel(writer, sheet_name='Temporary Posts', index=False)
            summary_df.to_excel(writer, sheet_name='Overall Summary', index=False)
        output.seek(0)

        logger.info("Excel file created, preparing response...")
        headers = {
            'Content-Disposition': 'attachment; filename="budget_summary_report.xlsx"'
        }
        return StreamingResponse(
            output,
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers=headers
        )

    except Exception as e:
        logger.error(f"Failed to generate Excel file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Could not generate Excel file: {e}")