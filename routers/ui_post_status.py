# routers/ui_post_status.py
from fastapi import APIRouter, Depends, Request, Form, HTTPException, status, Query, Response
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func, case, Integer, String # Add case, Integer, String
from typing import List, Optional, Dict, Any # Add Dict, Any
import models
import schemas
from database import get_db
from config import DISTRICTS, CATEGORIES, CLASSES_SHEET1_2, STATUSES # Removed unused limits
import pandas as pd
import io
from urllib.parse import urlencode
from collections import defaultdict # Add defaultdict
import logging # Optional: for logging
import json # For embedding chart data

templates = Jinja2Templates(directory="templates")
templates.env.globals['zip'] = zip # Make zip available if needed by template directly

router = APIRouter(
    prefix="/ui/post-status",
    tags=["UI - Post Status"],
    include_in_schema=False
)

logger = logging.getLogger(__name__) # Optional: for logging

# --- REVISED HELPER FUNCTION (Existing logic - returns data needed) ---
def get_post_status_summary_data(db: Session) -> Dict[str, Any]:
    logger.info("--- (Helper REVISED) Fetching post status summary data ---")
    try:
        # Define standard class keys and metric order
        CLASS_1_2_KEY = 'वर्ग-1 व 2'
        CLASS_3_KEY = 'वर्ग-3'
        CLASS_4_KEY = 'वर्ग-4'
        VALID_CLASS_KEYS = [CLASS_1_2_KEY, CLASS_3_KEY, CLASS_4_KEY]
        CLASS_MAPPING = {
            'Class-1 & 2': CLASS_1_2_KEY, 'Class-3': CLASS_3_KEY, 'Class-4': CLASS_4_KEY
        }
        METRICS_DB_KEYS = [ 'Posts', 'Salary', 'GradePay', 'DearnessAllowance', 'LocalSupplemetoryAllowance', 'HouseRentAllowance', 'TravelAllowance', 'Other' ]
        METRICS_LABELS = [ 'पदे', 'वेतन', 'ग्रेड पे', 'एकूण वेतन', 'विशेष वेतन', 'महा.भत्ता', 'स्था.पु.भ.', 'घरभाडे', 'प्रवास भत्ता', 'इतर', 'एकूण खर्च' ]

        # Query and aggregate data
        query_results = db.query(
            models.PostStatus.Category, models.PostStatus.Class, models.PostStatus.Status,
            func.sum(models.PostStatus.Posts).label("Posts"), func.sum(models.PostStatus.Salary).label("Salary"),
            func.sum(models.PostStatus.GradePay).label("GradePay"), func.sum(models.PostStatus.DearnessAllowance).label("DearnessAllowance"),
            func.sum(models.PostStatus.LocalSupplemetoryAllowance).label("LocalSupplemetoryAllowance"), func.sum(models.PostStatus.HouseRentAllowance).label("HouseRentAllowance"),
            func.sum(models.PostStatus.TravelAllowance).label("TravelAllowance"), func.sum(models.PostStatus.Other).label("Other")
        ).group_by( models.PostStatus.Category, models.PostStatus.Class, models.PostStatus.Status ).all()
        logger.info(f"(Helper REVISED) PostStatus query returned {len(query_results)} aggregated rows.")

        # Intermediate Aggregation
        summary = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(int))))
        for row in query_results:
            category = row.Category; raw_class = row.Class; status = row.Status; class_key = CLASS_MAPPING.get(raw_class)
            if not category or not class_key or not status: continue
            target = summary[category][class_key][status]
            for db_key in METRICS_DB_KEYS: target[db_key] = int(getattr(row, db_key) or 0)

        # Prepare Row-Based Output for Tables & Comparison Data
        permanent_metric_rows = []; temporary_metric_rows = []; comparison_metrics_keys = []
        perm_category_totals = defaultdict(int); temp_category_totals = defaultdict(int)

        for i, label in enumerate(METRICS_LABELS):
            perm_row = {'Label': label}; temp_row = {'Label': label}; metric_key_for_comp = None
            for class_key in VALID_CLASS_KEYS + ['एकूण']:
                is_total_col = (class_key == 'एकूण')
                perm_filled_data = defaultdict(int); perm_vacant_data = defaultdict(int); temp_filled_data = defaultdict(int); temp_vacant_data = defaultdict(int)
                if not is_total_col:
                    perm_filled_data = summary['Permanent'].get(class_key, {}).get('Filled', defaultdict(int)); perm_vacant_data = summary['Permanent'].get(class_key, {}).get('Vacant', defaultdict(int))
                    temp_filled_data = summary['Temporary'].get(class_key, {}).get('Filled', defaultdict(int)); temp_vacant_data = summary['Temporary'].get(class_key, {}).get('Vacant', defaultdict(int))
                else:
                    for ck in VALID_CLASS_KEYS:
                        for dbk in METRICS_DB_KEYS:
                             perm_filled_data[dbk] += summary['Permanent'].get(ck, {}).get('Filled', {}).get(dbk, 0); perm_vacant_data[dbk] += summary['Permanent'].get(ck, {}).get('Vacant', {}).get(dbk, 0)
                             temp_filled_data[dbk] += summary['Temporary'].get(ck, {}).get('Filled', {}).get(dbk, 0); temp_vacant_data[dbk] += summary['Temporary'].get(ck, {}).get('Vacant', {}).get(dbk, 0)

                # Determine value based on label (Logic remains same, ensures correct calculation)
                val_perm_filled, val_perm_vacant, val_temp_filled, val_temp_vacant = 0, 0, 0, 0
                if label == 'पदे': metric_key_for_comp = 'पदे'; val_perm_filled = perm_filled_data.get('Posts', 0); val_perm_vacant = perm_vacant_data.get('Posts', 0); val_temp_filled = temp_filled_data.get('Posts', 0); val_temp_vacant = temp_vacant_data.get('Posts', 0)
                elif label == 'वेतन': metric_key_for_comp = 'वेतन'; val_perm_filled = perm_filled_data.get('Salary', 0); val_temp_filled = temp_filled_data.get('Salary', 0); val_perm_vacant, val_temp_vacant = 0, 0
                elif label == 'ग्रेड पे': metric_key_for_comp = 'ग्रेड पे'; val_perm_filled = perm_filled_data.get('GradePay', 0); val_temp_filled = temp_filled_data.get('GradePay', 0); val_perm_vacant, val_temp_vacant = 0, 0
                elif label == 'एकूण वेतन': metric_key_for_comp = 'एकूण वेतन'; val_perm_filled = perm_filled_data.get('Salary', 0) + perm_filled_data.get('GradePay', 0); val_temp_filled = temp_filled_data.get('Salary', 0) + temp_filled_data.get('GradePay', 0); val_perm_vacant, val_temp_vacant = 0, 0
                elif label == 'विशेष वेतन': metric_key_for_comp = 'विशेष वेतन'; val_perm_filled, val_perm_vacant, val_temp_filled, val_temp_vacant = 0, 0, 0, 0 # Assumed 0
                elif label == 'महा.भत्ता': metric_key_for_comp = 'महा.भत्ता'; val_perm_filled = perm_filled_data.get('DearnessAllowance', 0); val_temp_filled = temp_filled_data.get('DearnessAllowance', 0); val_perm_vacant, val_temp_vacant = 0, 0
                elif label == 'स्था.पु.भ.': metric_key_for_comp = 'स्था.पु.भ.'; val_perm_filled = perm_filled_data.get('LocalSupplemetoryAllowance', 0); val_temp_filled = temp_filled_data.get('LocalSupplemetoryAllowance', 0); val_perm_vacant, val_temp_vacant = 0, 0
                elif label == 'घरभाडे': metric_key_for_comp = 'घरभाडे'; val_perm_filled = perm_filled_data.get('HouseRentAllowance', 0); val_temp_filled = temp_filled_data.get('HouseRentAllowance', 0); val_perm_vacant, val_temp_vacant = 0, 0
                elif label == 'प्रवास भत्ता': metric_key_for_comp = 'प्रवास भत्ता'; val_perm_filled = perm_filled_data.get('TravelAllowance', 0); val_temp_filled = temp_filled_data.get('TravelAllowance', 0); val_perm_vacant, val_temp_vacant = 0, 0
                elif label == 'इतर': metric_key_for_comp = 'इतर'; val_perm_filled = perm_filled_data.get('Other', 0); val_temp_filled = temp_filled_data.get('Other', 0); val_perm_vacant, val_temp_vacant = 0, 0
                elif label == 'एकूण खर्च': metric_key_for_comp = 'एकूण खर्च'; val_perm_filled = sum(perm_filled_data.get(k,0) for k in ['Salary','GradePay','DearnessAllowance','LocalSupplemetoryAllowance','HouseRentAllowance','TravelAllowance','Other']); val_temp_filled = sum(temp_filled_data.get(k,0) for k in ['Salary','GradePay','DearnessAllowance','LocalSupplemetoryAllowance','HouseRentAllowance','TravelAllowance','Other']); val_perm_vacant, val_temp_vacant = 0, 0

                # Assign values
                perm_row[f'Filled_{class_key}'] = val_perm_filled; perm_row[f'Vacant_{class_key}'] = val_perm_vacant
                temp_row[f'Filled_{class_key}'] = val_temp_filled; temp_row[f'Vacant_{class_key}'] = val_temp_vacant

                # Sum category totals
                if not is_total_col and metric_key_for_comp:
                     if metric_key_for_comp == 'पदे': perm_category_totals[metric_key_for_comp] += val_perm_filled + val_perm_vacant; temp_category_totals[metric_key_for_comp] += val_temp_filled + val_temp_vacant
                     else: perm_category_totals[metric_key_for_comp] += val_perm_filled; temp_category_totals[metric_key_for_comp] += val_temp_filled

            # Add category total for this metric row
            perm_row['Category_Total'] = perm_category_totals.get(metric_key_for_comp, 0)
            temp_row['Category_Total'] = temp_category_totals.get(metric_key_for_comp, 0)
            permanent_metric_rows.append(perm_row); temporary_metric_rows.append(temp_row)
            if metric_key_for_comp and metric_key_for_comp not in comparison_metrics_keys: comparison_metrics_keys.append(metric_key_for_comp)

        # Prepare Comparison Summary (Third Table)
        grand_totals_comparison = defaultdict(int)
        for key in comparison_metrics_keys: grand_totals_comparison[key] = perm_category_totals.get(key, 0) + temp_category_totals.get(key, 0)
        comparison_summary = [ {'वर्ग': 'स्थायी', **perm_category_totals}, {'वर्ग': 'अस्थायी', **temp_category_totals}, {'वर्ग': 'एकूण', **grand_totals_comparison} ]

        # Prepare Final Class Summary Table Data (Logic remains same)
        final_class_summary = []; grand_total_amt = 0; grand_total_post = 0
        for cat in ['Permanent', 'Temporary']:
            cat_label = 'स्थायी' if cat == 'Permanent' else 'अस्थायी'; cat_total_amt = 0; cat_total_post = 0
            for cls_key in VALID_CLASS_KEYS:
                 filled_data = summary.get(cat, {}).get(cls_key, {}).get('Filled', defaultdict(int)); vacant_data = summary.get(cat, {}).get(cls_key, {}).get('Vacant', defaultdict(int))
                 class_cat_total_amt = sum(filled_data.get(k,0) for k in ['Salary','GradePay','DearnessAllowance','LocalSupplemetoryAllowance','HouseRentAllowance','TravelAllowance','Other'])
                 class_cat_total_post = filled_data.get('Posts', 0) + vacant_data.get('Posts', 0)
                 final_class_summary.append({ "CategoryLabel": cat_label, "ClassKey": cls_key, "Amt": class_cat_total_amt, "Post": class_cat_total_post })
                 cat_total_amt += class_cat_total_amt; cat_total_post += class_cat_total_post
            final_class_summary.append({ "CategoryLabel": cat_label, "ClassKey": "एकूण", "Amt": cat_total_amt, "Post": cat_total_post, "is_total": True })
            grand_total_amt += cat_total_amt; grand_total_post += cat_total_post
        final_class_summary.append({ "CategoryLabel": "स्थायी + अस्थायी", "ClassKey": "", "Amt": grand_total_amt, "Post": grand_total_post, "is_grand_total": True })

        logger.info("(Helper REVISED) Post status summary data prepared successfully.")
        return {
            'permanent_metric_rows': permanent_metric_rows, 'temporary_metric_rows': temporary_metric_rows,
            'comparison_summary': comparison_summary, 'comparison_metrics_keys': comparison_metrics_keys,
            'final_class_summary_table': final_class_summary, 'raw_summary_dict': summary, # Pass raw data for chart prep
            'class_keys_order': VALID_CLASS_KEYS, 'grand_totals_comparison': dict(grand_totals_comparison)
        }

    except Exception as e:
        logger.error(f"(Helper REVISED) Error fetching/processing post status summary data: {e}", exc_info=True)
        return None
# --- END REVISED HELPER FUNCTION ---


# --- Updated Main GET Route ---
@router.get("", response_class=HTMLResponse)
async def ui_list_post_status(
    request: Request, db: Session = Depends(get_db), view: Optional[str] = Query("edit"),
    district: Optional[str] = Query(None), category: Optional[str] = Query(None),
    cls: Optional[str] = Query(None, alias="class"), status_filter: Optional[str] = Query(None, alias="status")
):
    context = { "request": request, "resource_name": "Post Status", "districts": DISTRICTS, "categories": CATEGORIES,
                "classes": CLASSES_SHEET1_2, "statuses": STATUSES, "current_district": district, "current_category": category,
                "current_class": cls, "current_status": status_filter, "view_mode": view }

    if view == "summary":
        logger.info("Requesting Post Status Summary view")
        summary_data = get_post_status_summary_data(db) # Call helper function
        if summary_data is None:
             logger.error("Failed to get summary data for HTML report.")
             raise HTTPException(status_code=500, detail="Could not generate Post Status summary data.")

        # --- Prepare Chart Data ---
        chart_data = {}
        try:
            raw_summary = summary_data.get('raw_summary_dict', {})
            class_keys = summary_data.get('class_keys_order', [])
            comparison_totals = summary_data.get('grand_totals_comparison', {})

            # 1. Pie Chart: Overall Posts (Filled vs Vacant)
            total_filled = 0; total_vacant = 0
            for cat in raw_summary:
                for cls_key in raw_summary[cat]:
                    total_filled += raw_summary[cat][cls_key].get('Filled', {}).get('Posts', 0)
                    total_vacant += raw_summary[cat][cls_key].get('Vacant', {}).get('Posts', 0)
            if total_filled > 0 or total_vacant > 0:
                # Use Marathi labels
                chart_data['pie_posts_status'] = {'भरलेली': total_filled, 'रिक्त': total_vacant}

            # 2. Stacked Bar: Posts by Class (Filled vs Vacant)
            posts_by_class = {"labels": class_keys, "भरलेली": [], "रिक्त": []} # Use Marathi labels as keys
            has_posts_by_class_data = False
            for cls_key in class_keys:
                filled_cls = 0; vacant_cls = 0
                for cat in raw_summary:
                    filled_cls += raw_summary[cat].get(cls_key, {}).get('Filled', {}).get('Posts', 0)
                    vacant_cls += raw_summary[cat].get(cls_key, {}).get('Vacant', {}).get('Posts', 0)
                posts_by_class['भरलेली'].append(filled_cls)
                posts_by_class['रिक्त'].append(vacant_cls)
                if filled_cls > 0 or vacant_cls > 0: has_posts_by_class_data = True
            if has_posts_by_class_data:
                chart_data['stacked_bar_posts_by_class'] = posts_by_class

            # 3. Pie Chart: Total Amount (Permanent vs Temporary)
            # Use the 'एकूण खर्च' (Grand Total Cost) from comparison totals
            perm_total_cost = summary_data.get('comparison_summary', [{}, {}, {}])[0].get('एकूण खर्च', 0)
            temp_total_cost = summary_data.get('comparison_summary', [{}, {}, {}])[1].get('एकूण खर्च', 0)
            if perm_total_cost > 0 or temp_total_cost > 0:
                # Use Marathi labels as keys
                chart_data['pie_amount_category'] = {'स्थायी': perm_total_cost, 'अस्थायी': temp_total_cost}

            logger.info(f"Prepared chart data for Post Status: {chart_data}")

        except Exception as e:
            logger.error(f"Error preparing chart data for Post Status: {e}", exc_info=True)
            chart_data = {}

        context["resource_name"] = "Post Status Summary"
        context.update(summary_data) # Pass table data
        context["chart_data"] = chart_data # Pass chart data

        logger.info("Rendering Post Status Summary view with charts")
        return templates.TemplateResponse("post_status_list.html", context)

    elif view == "edit":
        # (Edit view logic remains unchanged)
        logger.info("Requesting Post Status List (edit) view")
        query = db.query(models.PostStatus)
        if district: query = query.filter(models.PostStatus.District == district)
        if category: query = query.filter(models.PostStatus.Category == category)
        if cls: query = query.filter(models.PostStatus.Class == cls)
        if status_filter: query = query.filter(models.PostStatus.Status == status_filter)
        items = query.order_by(models.PostStatus.id).all()
        query_params = {"district": district, "category": category, "class": cls, "status": status_filter}
        filtered_params = {k: v for k, v in query_params.items() if v is not None}
        context["export_query_string_list"] = "?" + urlencode(filtered_params) if filtered_params else ""
        context["items"] = items
        context["chart_data"] = None
        logger.info(f"Rendering Post Status List (edit) view with {len(items)} items.")
        return templates.TemplateResponse("post_status_list.html", context)

    else: # Invalid view
         logger.warning(f"Invalid view parameter received: {view}")
         raise HTTPException(status_code=400, detail="Invalid view parameter. Use 'edit' or 'summary'.")


# --- Edit Form Route (GET) - Unchanged ---
# (Keep original code)
@router.get("/{id}/edit", response_class=HTMLResponse)
async def ui_edit_post_status_form(request: Request, id: int, db: Session = Depends(get_db)):
    item = db.query(models.PostStatus).filter(models.PostStatus.id == id).first()
    if not item: raise HTTPException(status_code=404, detail=f"Post Status with ID {id} not found")
    return templates.TemplateResponse("post_status_form.html", { "request": request, "districts": DISTRICTS, "categories": CATEGORIES, "classes": CLASSES_SHEET1_2, "statuses": STATUSES, "item": item, "resource_name": "Post Status" })

# --- Edit Form Submission Route (POST) - Unchanged (Redirects to Edit View) ---
# (Keep original code)
@router.post("/{id}/edit", response_class=RedirectResponse)
async def ui_update_post_status( request: Request, id: int, db: Session = Depends(get_db), District: str = Form(...), Category: str = Form(...), Class: str = Form(...), Status: str = Form(...), Posts: Optional[int] = Form(None), Salary: Optional[int] = Form(None), GradePay: Optional[int] = Form(None), DearnessAllowance: Optional[int] = Form(None), LocalSupplemetoryAllowance: Optional[int] = Form(None), HouseRentAllowance: Optional[int] = Form(None), TravelAllowance: Optional[int] = Form(None), Other: Optional[int] = Form(None) ):
    db_item = db.query(models.PostStatus).filter(models.PostStatus.id == id).first()
    if not db_item: raise HTTPException(status_code=404, detail=f"Post Status with ID {id} not found")
    try:
        update_dict = { "District": District, "Category": Category, "Class": Class, "Status": Status, "Posts": Posts, "Salary": Salary, "GradePay": GradePay, "DearnessAllowance": DearnessAllowance, "LocalSupplemetoryAllowance": LocalSupplemetoryAllowance, "HouseRentAllowance": HouseRentAllowance, "TravelAllowance": TravelAllowance, "Other": Other }
        for key, value in update_dict.items():
            if value is not None: setattr(db_item, key, value)
        db.commit(); db.refresh(db_item)
        return RedirectResponse(url=router.url_path_for("ui_list_post_status") + "?view=edit", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        db.rollback(); logger.error(f"Failed to update Post Status ID {id}: {e}", exc_info=True)
        return templates.TemplateResponse("post_status_form.html", { "request": request, "error": f"Failed to update record: {e}", "districts": DISTRICTS, "categories": CATEGORIES, "classes": CLASSES_SHEET1_2, "statuses": STATUSES, "item": db_item, "resource_name": "Post Status" }, status_code=400)


# --- Excel Download Route for Summary - Unchanged ---
# (Keep original code)
@router.get("/summary/export-excel", response_class=StreamingResponse)
async def export_post_status_summary_excel(db: Session = Depends(get_db)):
    logger.info("--- Entered export_post_status_summary_excel ---")
    summary_data = get_post_status_summary_data(db)
    if summary_data is None: raise HTTPException(status_code=500, detail="Could not generate summary data for download.")
    try:
        logger.info("Preparing data for Post Status Summary Excel...")
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            CLASS_KEYS_ORDER = ['वर्ग-1 व 2', 'वर्ग-3', 'वर्ग-4', 'एकूण']; METRICS_ORDER_COMP = summary_data.get('comparison_metrics_keys', [])
            perm_rows_df = pd.DataFrame(summary_data['permanent_metric_rows']); cols_perm = ['Label'] + [f'{stat}_{cls}' for stat in ['Filled', 'Vacant'] for cls in CLASS_KEYS_ORDER] + ['Category_Total']; perm_rows_df = perm_rows_df[cols_perm]; perm_rows_df.to_excel(writer, sheet_name='Permanent Posts Summary', index=False)
            temp_rows_df = pd.DataFrame(summary_data['temporary_metric_rows']); cols_temp = ['Label'] + [f'{stat}_{cls}' for stat in ['Filled', 'Vacant'] for cls in CLASS_KEYS_ORDER] + ['Category_Total']; temp_rows_df = temp_rows_df[cols_temp]; temp_rows_df.to_excel(writer, sheet_name='Temporary Posts Summary', index=False)
            comp_df = pd.DataFrame(summary_data['comparison_summary']);
            if METRICS_ORDER_COMP: comp_df = comp_df[['वर्ग'] + METRICS_ORDER_COMP]; comp_df.to_excel(writer, sheet_name='Overall Comparison', index=False)
            final_sum_df = pd.DataFrame(summary_data['final_class_summary_table']); final_sum_df = final_sum_df[['CategoryLabel', 'ClassKey', 'Amt', 'Post']]; final_sum_df.columns = ['Category', 'Class', 'Amount', 'Posts']; final_sum_df.to_excel(writer, sheet_name='Final Class Summary', index=False)
        output.seek(0); logger.info("Post Status Summary Excel file created, preparing response...")
        headers = {'Content-Disposition': 'attachment; filename="post_status_summary_report.xlsx"'}
        return StreamingResponse(output, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    except Exception as e:
        logger.error(f"Failed to generate Post Status Summary Excel file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Could not generate Excel file: {e}")

# --- Excel Download Route for List View - Unchanged ---
# (Keep original code)
@router.get("/list/export-excel", response_class=StreamingResponse)
async def export_post_status_list_excel( db: Session = Depends(get_db), district: Optional[str] = Query(None), category: Optional[str] = Query(None), cls: Optional[str] = Query(None, alias="class"), status_filter: Optional[str] = Query(None, alias="status") ):
    logger.info("--- Entered export_post_status_LIST_excel ---")
    query = db.query(models.PostStatus);
    if district: query = query.filter(models.PostStatus.District == district)
    if category: query = query.filter(models.PostStatus.Category == category)
    if cls: query = query.filter(models.PostStatus.Class == cls)
    if status_filter: query = query.filter(models.PostStatus.Status == status_filter)
    items = query.order_by(models.PostStatus.id).all(); data_dict_list = []
    if items: columns = [c.name for c in models.PostStatus.__table__.columns];
    for item in items: data_dict_list.append({col: getattr(item, col, None) for col in columns})
    df = pd.DataFrame(data_dict_list); output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer: df.to_excel(writer, sheet_name='Post Status List', index=False)
    output.seek(0); headers = {'Content-Disposition': 'attachment; filename="post_status_list.xlsx"'}
    return StreamingResponse(output, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')