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


# Assuming templates instance is created elsewhere (e.g., main.py) and accessible
# If not, uncomment and potentially add 'zip' to env globals here or in main.py
templates = Jinja2Templates(directory="templates")
# If templates is defined here and not globally:
# templates.env.globals['zip'] = zip # Make sure zip is available if needed elsewhere


router = APIRouter(
    prefix="/ui/post-status",
    tags=["UI - Post Status"],
    include_in_schema=False
)

logger = logging.getLogger(__name__) # Optional: for logging

# --- REVISED HELPER FUNCTION ---
def get_post_status_summary_data(db: Session) -> Dict[str, Any]:
    logger.info("--- (Helper REVISED) Fetching post status summary data ---")
    try:
        # Define standard class keys and metric order
        CLASS_1_2_KEY = 'वर्ग-1 व 2'
        CLASS_3_KEY = 'वर्ग-3'
        CLASS_4_KEY = 'वर्ग-4'
        VALID_CLASS_KEYS = [CLASS_1_2_KEY, CLASS_3_KEY, CLASS_4_KEY]
        CLASS_MAPPING = {
            'Class-1 & 2': CLASS_1_2_KEY,
            'Class-3': CLASS_3_KEY,
            'Class-4': CLASS_4_KEY
        }

        # Define the order and labels for metrics (rows in the first two tables)
        METRICS_DB_KEYS = [ # Order matters! Matches the calculation dependencies
            'Posts', 'Salary', 'GradePay', 'DearnessAllowance',
            'LocalSupplemetoryAllowance', 'HouseRentAllowance',
            'TravelAllowance', 'Other'
        ]
        METRICS_LABELS = [ # Display names for rows
            'पदे', 'वेतन', 'ग्रेड पे', 'एकूण', 'विशेष वेतन', 'महा.भत्ता',
            'स्था.पु.भ.', 'घरभाडे', 'प्रवास भत्ता', 'इतर', 'एकूण'
        ]
        CALCULATED_METRIC_KEYS = [ # Derived metrics
            'TotalPay', 'SpecialPay', 'GrandTotal'
        ]
        # Full list of keys expected in the final row dictionaries for tables 1 & 2
        ALL_ROW_METRIC_KEYS = ['पदे', 'वेतन', 'ग्रेड पे', 'एकूण वेतन', 'विशेष वेतन', 'महा.भत्ता', 'स्था.पु.भ.', 'घरभाडे', 'प्रवास भत्ता', 'इतर', 'एकूण खर्च']


        # Query and aggregate data from PostStatus model
        query_results = db.query(
            models.PostStatus.Category,
            models.PostStatus.Class,
            models.PostStatus.Status,
            # Summing based on DB keys
            func.sum(models.PostStatus.Posts).label("Posts"),
            func.sum(models.PostStatus.Salary).label("Salary"),
            func.sum(models.PostStatus.GradePay).label("GradePay"),
            func.sum(models.PostStatus.DearnessAllowance).label("DearnessAllowance"),
            func.sum(models.PostStatus.LocalSupplemetoryAllowance).label("LocalSupplemetoryAllowance"),
            func.sum(models.PostStatus.HouseRentAllowance).label("HouseRentAllowance"),
            func.sum(models.PostStatus.TravelAllowance).label("TravelAllowance"),
            func.sum(models.PostStatus.Other).label("Other")
        ).group_by(
            models.PostStatus.Category,
            models.PostStatus.Class,
            models.PostStatus.Status
        ).all()
        logger.info(f"(Helper REVISED) PostStatus query returned {len(query_results)} aggregated rows.")

        # --- Intermediate Aggregation ---
        # Structure: summary[category][class_key][status][db_metric_key]
        summary = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(int))))
        for row in query_results:
            category = row.Category
            raw_class = row.Class
            status = row.Status # 'Filled' or 'Vacant'
            class_key = CLASS_MAPPING.get(raw_class)
            if not category or not class_key or not status: continue

            target = summary[category][class_key][status]
            for db_key in METRICS_DB_KEYS:
                target[db_key] = int(getattr(row, db_key) or 0)

        # --- Prepare Row-Based Output for Tables 1 & 2 ---
        permanent_metric_rows = []
        temporary_metric_rows = []
        comparison_metrics_keys = [] # Will store keys for table 3

        # Initialize grand totals for comparison table
        perm_category_totals = defaultdict(int)
        temp_category_totals = defaultdict(int)

        # Calculate row data
        for i, label in enumerate(METRICS_LABELS):
            perm_row = {'Label': label}
            temp_row = {'Label': label}
            metric_key_for_comp = None # Key to use for comparison table

            # Loop through classes and statuses to populate the row dict
            for class_key in VALID_CLASS_KEYS + ['एकूण']: # Include total column
                # Calculate totals dynamically if 'एकूण' column
                is_total_col = (class_key == 'एकूण')

                # Initialize dictionaries to store data for the current class/total column
                perm_filled_data = defaultdict(int)
                perm_vacant_data = defaultdict(int)
                temp_filled_data = defaultdict(int)
                temp_vacant_data = defaultdict(int)

                # Get data or calculate totals
                if not is_total_col:
                    perm_filled_data = summary['Permanent'].get(class_key, {}).get('Filled', defaultdict(int))
                    perm_vacant_data = summary['Permanent'].get(class_key, {}).get('Vacant', defaultdict(int))
                    temp_filled_data = summary['Temporary'].get(class_key, {}).get('Filled', defaultdict(int))
                    temp_vacant_data = summary['Temporary'].get(class_key, {}).get('Vacant', defaultdict(int))
                else: # Calculate total column
                    for ck in VALID_CLASS_KEYS:
                        for dbk in METRICS_DB_KEYS:
                             perm_filled_data[dbk] += summary['Permanent'].get(ck, {}).get('Filled', {}).get(dbk, 0)
                             perm_vacant_data[dbk] += summary['Permanent'].get(ck, {}).get('Vacant', {}).get(dbk, 0)
                             temp_filled_data[dbk] += summary['Temporary'].get(ck, {}).get('Filled', {}).get(dbk, 0)
                             temp_vacant_data[dbk] += summary['Temporary'].get(ck, {}).get('Vacant', {}).get(dbk, 0)


                # Determine value based on label
                val_perm_filled, val_perm_vacant, val_temp_filled, val_temp_vacant = 0, 0, 0, 0

                if label == 'पदे':
                     metric_key_for_comp = 'पदे'
                     val_perm_filled = perm_filled_data.get('Posts', 0)
                     val_perm_vacant = perm_vacant_data.get('Posts', 0)
                     val_temp_filled = temp_filled_data.get('Posts', 0)
                     val_temp_vacant = temp_vacant_data.get('Posts', 0)
                elif label == 'वेतन':
                    metric_key_for_comp = 'वेतन'
                    val_perm_filled = perm_filled_data.get('Salary', 0)
                    val_perm_vacant = perm_vacant_data.get('Salary', 0)
                    val_temp_filled = temp_filled_data.get('Salary', 0)
                    val_temp_vacant = temp_vacant_data.get('Salary', 0)
                elif label == 'ग्रेड पे':
                    metric_key_for_comp = 'ग्रेड पे'
                    val_perm_filled = perm_filled_data.get('GradePay', 0)
                    val_perm_vacant = perm_vacant_data.get('GradePay', 0)
                    val_temp_filled = temp_filled_data.get('GradePay', 0)
                    val_temp_vacant = temp_vacant_data.get('GradePay', 0)
                elif label == 'एकूण' and i == 3: # First 'एकूण' (Total Pay)
                    metric_key_for_comp = 'एकूण वेतन'
                    val_perm_filled = perm_filled_data.get('Salary', 0) + perm_filled_data.get('GradePay', 0)
                    val_perm_vacant = perm_vacant_data.get('Salary', 0) + perm_vacant_data.get('GradePay', 0)
                    val_temp_filled = temp_filled_data.get('Salary', 0) + temp_filled_data.get('GradePay', 0)
                    val_temp_vacant = temp_vacant_data.get('Salary', 0) + temp_vacant_data.get('GradePay', 0)
                elif label == 'विशेष वेतन': # Assumed 0
                     metric_key_for_comp = 'विशेष वेतन'
                     val_perm_filled, val_perm_vacant, val_temp_filled, val_temp_vacant = 0, 0, 0, 0
                elif label == 'महा.भत्ता':
                    metric_key_for_comp = 'महा.भत्ता'
                    val_perm_filled = perm_filled_data.get('DearnessAllowance', 0)
                    val_perm_vacant = perm_vacant_data.get('DearnessAllowance', 0)
                    val_temp_filled = temp_filled_data.get('DearnessAllowance', 0)
                    val_temp_vacant = temp_vacant_data.get('DearnessAllowance', 0)
                elif label == 'स्था.पु.भ.':
                    metric_key_for_comp = 'स्था.पु.भ.'
                    val_perm_filled = perm_filled_data.get('LocalSupplemetoryAllowance', 0)
                    val_perm_vacant = perm_vacant_data.get('LocalSupplemetoryAllowance', 0)
                    val_temp_filled = temp_filled_data.get('LocalSupplemetoryAllowance', 0)
                    val_temp_vacant = temp_vacant_data.get('LocalSupplemetoryAllowance', 0)
                elif label == 'घरभाडे':
                    metric_key_for_comp = 'घरभाडे'
                    val_perm_filled = perm_filled_data.get('HouseRentAllowance', 0)
                    val_perm_vacant = perm_vacant_data.get('HouseRentAllowance', 0)
                    val_temp_filled = temp_filled_data.get('HouseRentAllowance', 0)
                    val_temp_vacant = temp_vacant_data.get('HouseRentAllowance', 0)
                elif label == 'प्रवास भत्ता':
                    metric_key_for_comp = 'प्रवास भत्ता'
                    val_perm_filled = perm_filled_data.get('TravelAllowance', 0)
                    val_perm_vacant = perm_vacant_data.get('TravelAllowance', 0)
                    val_temp_filled = temp_filled_data.get('TravelAllowance', 0)
                    val_temp_vacant = temp_vacant_data.get('TravelAllowance', 0)
                elif label == 'इतर':
                    metric_key_for_comp = 'इतर'
                    val_perm_filled = perm_filled_data.get('Other', 0)
                    val_perm_vacant = perm_vacant_data.get('Other', 0)
                    val_temp_filled = temp_filled_data.get('Other', 0)
                    val_temp_vacant = temp_vacant_data.get('Other', 0)
                elif label == 'एकूण' and i == 10: # Second 'एकूण' (Grand Total row)
                    metric_key_for_comp = 'एकूण खर्च'
                    # Calculate total based on previous rows logic (TotalPay + DA + LocalSupp + HRA + Travel + Other)
                    pf_tp = perm_filled_data.get('Salary', 0) + perm_filled_data.get('GradePay', 0)
                    pv_tp = perm_vacant_data.get('Salary', 0) + perm_vacant_data.get('GradePay', 0)
                    tf_tp = temp_filled_data.get('Salary', 0) + temp_filled_data.get('GradePay', 0)
                    tv_tp = temp_vacant_data.get('Salary', 0) + temp_vacant_data.get('GradePay', 0)

                    # Sum components for grand total
                    val_perm_filled = pf_tp + perm_filled_data.get('DearnessAllowance', 0) + perm_filled_data.get('LocalSupplemetoryAllowance', 0) + perm_filled_data.get('HouseRentAllowance', 0) + perm_filled_data.get('TravelAllowance', 0) + perm_filled_data.get('Other', 0)
                    val_perm_vacant = pv_tp + perm_vacant_data.get('DearnessAllowance', 0) + perm_vacant_data.get('LocalSupplemetoryAllowance', 0) + perm_vacant_data.get('HouseRentAllowance', 0) + perm_vacant_data.get('TravelAllowance', 0) + perm_vacant_data.get('Other', 0)
                    val_temp_filled = tf_tp + temp_filled_data.get('DearnessAllowance', 0) + temp_filled_data.get('LocalSupplemetoryAllowance', 0) + temp_filled_data.get('HouseRentAllowance', 0) + temp_filled_data.get('TravelAllowance', 0) + temp_filled_data.get('Other', 0)
                    val_temp_vacant = tv_tp + temp_vacant_data.get('DearnessAllowance', 0) + temp_vacant_data.get('LocalSupplemetoryAllowance', 0) + temp_vacant_data.get('HouseRentAllowance', 0) + temp_vacant_data.get('TravelAllowance', 0) + temp_vacant_data.get('Other', 0)


                # Assign values to the row dictionary using descriptive keys for the template
                perm_row[f'Filled_{class_key}'] = val_perm_filled
                perm_row[f'Vacant_{class_key}'] = val_perm_vacant
                temp_row[f'Filled_{class_key}'] = val_temp_filled
                temp_row[f'Vacant_{class_key}'] = val_temp_vacant

                # Sum category totals (only for non-total columns)
                if not is_total_col and metric_key_for_comp:
                    perm_category_totals[metric_key_for_comp] += val_perm_filled + val_perm_vacant
                    temp_category_totals[metric_key_for_comp] += val_temp_filled + val_temp_vacant

            # Add the category total for this metric row
            perm_row['Category_Total'] = perm_category_totals.get(metric_key_for_comp, 0)
            temp_row['Category_Total'] = temp_category_totals.get(metric_key_for_comp, 0)

            # Append the completed row for this metric
            permanent_metric_rows.append(perm_row)
            temporary_metric_rows.append(temp_row)
            # Store the key used for comparison table
            if metric_key_for_comp and metric_key_for_comp not in comparison_metrics_keys:
                 comparison_metrics_keys.append(metric_key_for_comp)


        # --- Prepare Comparison Summary (Third Table) ---
        grand_totals_comparison = defaultdict(int)
        for key in comparison_metrics_keys:
             grand_totals_comparison[key] = perm_category_totals.get(key, 0) + temp_category_totals.get(key, 0)

        comparison_summary = [
            {'वर्ग': 'स्थायी पदे', **perm_category_totals},
            {'वर्ग': 'अस्थायी पदे', **temp_category_totals},
            {'वर्ग': 'एकूण', **grand_totals_comparison}
        ]

        # --- Prepare Final Class Summary Table Data ---
        final_class_summary = []
        grand_total_amt = 0
        grand_total_post = 0
        for cat in ['Permanent', 'Temporary']:
            cat_label = 'स्थायी' if cat == 'Permanent' else 'अस्थायी'
            cat_total_amt = 0
            cat_total_post = 0
            for cls_key in VALID_CLASS_KEYS:
                 filled_data = summary.get(cat, {}).get(cls_key, {}).get('Filled', defaultdict(int))
                 vacant_data = summary.get(cat, {}).get(cls_key, {}).get('Vacant', defaultdict(int))

                 # Recalculate total amount for this class/cat based on the grand total row logic
                 pf_tp = filled_data.get('Salary', 0) + filled_data.get('GradePay', 0)
                 pv_tp = vacant_data.get('Salary', 0) + vacant_data.get('GradePay', 0)
                 class_cat_total_amt = (pf_tp + filled_data.get('DearnessAllowance', 0) + filled_data.get('LocalSupplemetoryAllowance', 0) + filled_data.get('HouseRentAllowance', 0) + filled_data.get('TravelAllowance', 0) + filled_data.get('Other', 0)) + \
                                       (pv_tp + vacant_data.get('DearnessAllowance', 0) + vacant_data.get('LocalSupplemetoryAllowance', 0) + vacant_data.get('HouseRentAllowance', 0) + vacant_data.get('TravelAllowance', 0) + vacant_data.get('Other', 0))

                 class_cat_total_post = filled_data.get('Posts', 0) + vacant_data.get('Posts', 0)

                 final_class_summary.append({
                     "CategoryLabel": cat_label, "ClassKey": cls_key,
                     "Amt": class_cat_total_amt, "Post": class_cat_total_post
                 })
                 cat_total_amt += class_cat_total_amt
                 cat_total_post += class_cat_total_post

            # Add category total row
            final_class_summary.append({
                "CategoryLabel": cat_label, "ClassKey": "एकूण",
                "Amt": cat_total_amt, "Post": cat_total_post,
                "is_total": True
            })
            grand_total_amt += cat_total_amt
            grand_total_post += cat_total_post

        # Add Grand Total row
        final_class_summary.append({
            "CategoryLabel": "स्थायी + अस्थायी", "ClassKey": "",
            "Amt": grand_total_amt, "Post": grand_total_post,
            "is_grand_total": True
        })

        logger.info("(Helper REVISED) Post status summary data prepared successfully.")
        return {
            'permanent_metric_rows': permanent_metric_rows,
            'temporary_metric_rows': temporary_metric_rows,
            'comparison_summary': comparison_summary,
            'comparison_metrics_keys': comparison_metrics_keys, # Pass keys for table 3 iteration
            'final_class_summary_table': final_class_summary
        }

    except Exception as e:
        logger.error(f"(Helper REVISED) Error fetching/processing post status summary data: {e}", exc_info=True)
        return None
# --- END REVISED HELPER FUNCTION ---


# --- Updated Main GET Route ---
@router.get("", response_class=HTMLResponse)
async def ui_list_post_status(
    request: Request,
    db: Session = Depends(get_db),
    view: Optional[str] = Query("edit"), # Default to list view
    district: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    cls: Optional[str] = Query(None, alias="class"),
    status_filter: Optional[str] = Query(None, alias="status")
):
    context = {
        "request": request,
        "resource_name": "Post Status", # Will be overridden in summary view
        "districts": DISTRICTS,
        "categories": CATEGORIES,
        "classes": CLASSES_SHEET1_2, # Classes for filtering the list view
        "statuses": STATUSES,
        "current_district": district,
        "current_category": category,
        "current_class": cls,
        "current_status": status_filter,
        "view_mode": view # Pass current view mode to template
    }

    if view == "summary":
        logger.info("Requesting Post Status Summary view")
        summary_data = get_post_status_summary_data(db)
        if summary_data is None:
             logger.error("Failed to get summary data from helper.")
             raise HTTPException(status_code=500, detail="Could not generate Post Status summary data.")

        context["resource_name"] = "Post Status Summary"
        context.update(summary_data) # Add all summary data parts to context
        logger.info("Rendering Post Status Summary view")
        return templates.TemplateResponse("post_status_list.html", context)

    elif view == "edit":
        logger.info("Requesting Post Status List (edit) view")
        query = db.query(models.PostStatus)
        if district: query = query.filter(models.PostStatus.District == district)
        if category: query = query.filter(models.PostStatus.Category == category)
        if cls: query = query.filter(models.PostStatus.Class == cls)
        if status_filter: query = query.filter(models.PostStatus.Status == status_filter)

        items = query.order_by(models.PostStatus.id).all()

        # Ensure view=edit is part of the export query string for the list view
        query_params = {"district": district, "category": category, "class": cls, "status": status_filter}
        filtered_params = {k: v for k, v in query_params.items() if v is not None}
        # Always include view=edit for the list export link's base
        export_query_string = "?" + urlencode({"view": "edit", **filtered_params})


        context["items"] = items
        # Correctly pass the export query string for the list view export button
        context["export_query_string_list"] = "?" + urlencode(filtered_params) if filtered_params else ""


        logger.info(f"Rendering Post Status List (edit) view with {len(items)} items.")
        return templates.TemplateResponse("post_status_list.html", context)

    else:
         logger.warning(f"Invalid view parameter received: {view}")
         raise HTTPException(status_code=400, detail="Invalid view parameter. Use 'edit' or 'summary'.")


# --- Edit Form Route (GET) ---
@router.get("/{id}/edit", response_class=HTMLResponse)
async def ui_edit_post_status_form(request: Request, id: int, db: Session = Depends(get_db)):
    item = db.query(models.PostStatus).filter(models.PostStatus.id == id).first()
    if not item:
        raise HTTPException(status_code=404, detail=f"Post Status with ID {id} not found")
    return templates.TemplateResponse("post_status_form.html", {
        "request": request,
        "districts": DISTRICTS,
        "categories": CATEGORIES,
        "classes": CLASSES_SHEET1_2,
        "statuses": STATUSES,
        "item": item,
        "resource_name": "Post Status" # Keep consistent title for edit form
    })

# --- Edit Form Submission Route (POST) ---
@router.post("/{id}/edit", response_class=HTMLResponse) # Changed to HTMLResponse to handle potential errors
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
    DearnessAllowance: Optional[int] = Form(None),
    LocalSupplemetoryAllowance: Optional[int] = Form(None),
    HouseRentAllowance: Optional[int] = Form(None),
    TravelAllowance: Optional[int] = Form(None),
    Other: Optional[int] = Form(None)
):
    db_item = db.query(models.PostStatus).filter(models.PostStatus.id == id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail=f"Post Status with ID {id} not found")

    try:
        # Use the Pydantic schema for validation if available and applicable
        # Here, we directly update attributes for simplicity
        update_dict = {
            "District": District, "Category": Category, "Class": Class, "Status": Status,
            "Posts": Posts, "Salary": Salary, "GradePay": GradePay,
            "DearnessAllowance": DearnessAllowance,
            "LocalSupplemetoryAllowance": LocalSupplemetoryAllowance,
            "HouseRentAllowance": HouseRentAllowance,
            "TravelAllowance": TravelAllowance, "Other": Other
        }

        for key, value in update_dict.items():
            # Only update if the value is provided (Form sends None for empty optional numbers)
            if value is not None:
                setattr(db_item, key, value)

        db.commit()
        db.refresh(db_item)
        # Redirect back to the list view (edit mode) upon successful update
        return RedirectResponse(url=router.url_path_for("ui_list_post_status") + "?view=edit", status_code=status.HTTP_303_SEE_OTHER)

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update Post Status ID {id}: {e}", exc_info=True)
        # Re-render the form with an error message
        return templates.TemplateResponse("post_status_form.html", {
            "request": request, "error": f"Failed to update record: {e}",
            "districts": DISTRICTS, "categories": CATEGORIES, "classes": CLASSES_SHEET1_2,
            "statuses": STATUSES, "item": db_item, # Pass the original item back
            "resource_name": "Post Status"
        }, status_code=400) # Indicate bad request/validation error


# --- NEW Excel Download Route for Summary ---
@router.get("/summary/export-excel", response_class=StreamingResponse)
async def export_post_status_summary_excel(db: Session = Depends(get_db)):
    logger.info("--- Entered export_post_status_summary_excel ---")
    summary_data = get_post_status_summary_data(db)

    if summary_data is None:
        logger.error("Failed to get summary data for Excel download.")
        raise HTTPException(status_code=500, detail="Could not generate summary data for download.")

    try:
        logger.info("Preparing data for Post Status Summary Excel...")
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Define standard class keys and metrics order for Excel export consistency
            CLASS_KEYS_ORDER = ['वर्ग-1 व 2', 'वर्ग-3', 'वर्ग-4', 'एकूण']
             # Use the keys passed from the helper for the comparison table
            METRICS_ORDER_COMP = summary_data.get('comparison_metrics_keys', [])

            # --- Sheet 1: Permanent Posts (Row-based structure) ---
            perm_rows_df = pd.DataFrame(summary_data['permanent_metric_rows'])
            # Construct column order dynamically based on expected keys
            cols_perm = ['Label'] + [f'{stat}_{cls}' for stat in ['Filled', 'Vacant'] for cls in CLASS_KEYS_ORDER] + ['Category_Total']
            perm_rows_df = perm_rows_df[cols_perm] # Select and order columns
            perm_rows_df.to_excel(writer, sheet_name='Permanent Posts Summary', index=False)

            # --- Sheet 2: Temporary Posts (Row-based structure) ---
            temp_rows_df = pd.DataFrame(summary_data['temporary_metric_rows'])
            cols_temp = ['Label'] + [f'{stat}_{cls}' for stat in ['Filled', 'Vacant'] for cls in CLASS_KEYS_ORDER] + ['Category_Total']
            temp_rows_df = temp_rows_df[cols_temp] # Select and order columns
            temp_rows_df.to_excel(writer, sheet_name='Temporary Posts Summary', index=False)


            # --- Sheet 3: Comparison Summary ---
            comp_df = pd.DataFrame(summary_data['comparison_summary'])
            if METRICS_ORDER_COMP: # Ensure keys exist before selecting
                 comp_df = comp_df[['वर्ग'] + METRICS_ORDER_COMP] # Order columns
            comp_df.to_excel(writer, sheet_name='Overall Comparison', index=False)

            # --- Sheet 4: Final Class Summary Table ---
            final_sum_df = pd.DataFrame(summary_data['final_class_summary_table'])
            # Reorder columns for clarity
            final_sum_df = final_sum_df[['CategoryLabel', 'ClassKey', 'Amt', 'Post']]
            final_sum_df.columns = ['Category', 'Class', 'Amount', 'Posts'] # Rename columns
            final_sum_df.to_excel(writer, sheet_name='Final Class Summary', index=False)


        output.seek(0)
        logger.info("Post Status Summary Excel file created, preparing response...")
        headers = {'Content-Disposition': 'attachment; filename="post_status_summary_report.xlsx"'}
        return StreamingResponse(output, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    except Exception as e:
        logger.error(f"Failed to generate Post Status Summary Excel file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Could not generate Excel file: {e}")


# --- Existing Excel Download Route for List View (Make sure URL doesn't clash) ---
# Keep the existing one, maybe rename its path slightly if needed, or ensure the query params differ
@router.get("/list/export-excel", response_class=StreamingResponse) # Example: changed path slightly
async def export_post_status_list_excel(
    db: Session = Depends(get_db),
    district: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    cls: Optional[str] = Query(None, alias="class"),
    status_filter: Optional[str] = Query(None, alias="status")
):
    logger.info("--- Entered export_post_status_LIST_excel ---") # Log difference
    query = db.query(models.PostStatus)
    if district: query = query.filter(models.PostStatus.District == district)
    if category: query = query.filter(models.PostStatus.Category == category)
    if cls: query = query.filter(models.PostStatus.Class == cls)
    if status_filter: query = query.filter(models.PostStatus.Status == status_filter)
    items = query.order_by(models.PostStatus.id).all()

    # Simple dict conversion and cleanup
    data_dict_list = []
    if items:
        columns = [c.name for c in models.PostStatus.__table__.columns]
        for item in items:
            data_dict_list.append({col: getattr(item, col, None) for col in columns})

    df = pd.DataFrame(data_dict_list)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Post Status List', index=False)
    output.seek(0)
    headers = {'Content-Disposition': 'attachment; filename="post_status_list.xlsx"'} # Different filename
    return StreamingResponse(output, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

# --- End Excel ---