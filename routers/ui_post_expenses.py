from fastapi import APIRouter, Depends, Request, Form, HTTPException, status, Query, Response
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func, case, Integer, String, Float # Add Float
from sqlalchemy.sql.expression import literal_column # Add literal_column for COALESCE with specific type
from typing import List, Optional, Dict, Any # Add Dict, Any
import models # Import models including the new one
import schemas
from database import get_db
from config import DISTRICTS, CATEGORIES, CLASSES_SHEET3 # Removed unused limit
import pandas as pd
import io
from urllib.parse import urlencode
from collections import defaultdict # Add defaultdict
import logging # Optional: for logging

templates = Jinja2Templates(directory="templates")

router = APIRouter(
    prefix="/ui/post-expenses",
    tags=["UI - Post Expenses"],
    include_in_schema=False
)

logger = logging.getLogger(__name__) # Optional: for logging

# --- REVISED HELPER FUNCTION v3 (Fetches Table 2 data) ---
def get_post_expenses_summary_data(db: Session) -> Dict[str, Any]:
    logger.info("--- (Helper REVISED v3) Fetching post expenses summary data ---")
    try:
        # --- Aggregation for Table 1 (Post Counts - Remains the same) ---
        post_counts_query = db.query(
            models.PostExpenses.Class,
            models.PostExpenses.Category,
            func.sum(models.PostExpenses.FilledPosts).label("TotalFilled"),
            func.sum(models.PostExpenses.VacantPosts).label("TotalVacant")
        ).group_by(
            models.PostExpenses.Class,
            models.PostExpenses.Category
        ).all()

        # --- Fetch Data for Table 2 (Approved Post Targets) ---
        approved_targets_query = db.query(models.ApprovedPostTarget).all()
        # Structure fetched data for easy access: target_data[class_key][category] = count
        target_data = defaultdict(lambda: defaultdict(int))
        for target in approved_targets_query:
            target_data[target.class_key][target.category] = target.approved_count

        # --- Fetch and Process Data for Table 3 (Expense Summary - Same as v2) ---
        # Fetch relevant columns for all districts to find unique values per district
        # Use simpler query first, process in Python
        expense_data_query = db.query(
            models.PostExpenses.District,
            models.PostExpenses.MedicalExpenses,
            models.PostExpenses.FestivalAdvance,
            models.PostExpenses.SwagramMaharashtraDarshan,
            models.PostExpenses.SeventhPayCommissionDifferenceNPS,
            models.PostExpenses.NPS,
            models.PostExpenses.SeventhPayCommissionDifference,
            models.PostExpenses.Other
        ).all()


        logger.info(f"(Helper REVISED v3) Post counts query returned {len(post_counts_query)} rows.")
        logger.info(f"(Helper REVISED v3) Approved targets query returned {len(approved_targets_query)} rows.")
        logger.info(f"(Helper REVISED v3) Base expense data query returned {len(expense_data_query)} rows for processing.")

        # --- Process Data for Table 1 (Remains the same) ---
        table1_data = defaultdict(lambda: defaultdict(int))
        for row in post_counts_query:
            cls = row.Class # '1', '2', '3', '4'
            cat = row.Category # 'Permanent', 'Temporary'
            if cls not in ['1', '2', '3', '4']: continue # Skip unexpected classes

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

            # Summing for footer totals
            for key in ["Permanent_Filled", "Permanent_Vacant", "Temporary_Filled", "Temporary_Vacant", "Row_Total"]:
                table1_totals[key] += row_data[key]

        table1_totals["SrNo"] = "--"
        table1_totals["Class"] = "एकूण"

        # --- Process Data for Table 2 (Using Fetched Targets) ---
        class_map_mr = {'1': 'वर्ग-1', '2': 'वर्ग-2', '3': 'वर्ग-3', '4': 'वर्ग-4'}
        table2_rows = []
        table2_totals = defaultdict(int)
        for cls in ['1', '2', '3', '4']:
            perm_approved = target_data[cls].get("Permanent", 0) # Fetch from target_data
            temp_approved = target_data[cls].get("Temporary", 0) # Fetch from target_data
            row_data = {
                "ClassKey": cls, # Store original key for update logic if needed
                "CadreLabel": class_map_mr.get(cls, cls), # Marathi label
                "Approved_Permanent": perm_approved,
                "Approved_Temporary": temp_approved,
                "Approved_Total": perm_approved + temp_approved # Calculate total dynamically
            }
            table2_rows.append(row_data)
            # Summing for footer totals based on fetched data
            table2_totals["Approved_Permanent"] += perm_approved
            table2_totals["Approved_Temporary"] += temp_approved
            table2_totals["Approved_Total"] += row_data["Approved_Total"]

        table2_totals["CadreLabel"] = "एकूण" # Marathi label for total row


        # --- Process Data for Table 3 (New Logic: Sum unique per-district values) ---
        table3_totals = defaultdict(float) # Use float for potential decimals
        processed_districts = set()
        unique_district_values = {} # Store the first value found for each district

        for row in expense_data_query:
            district = row.District
            if not district: continue # Skip rows without district

            if district not in processed_districts:
                 unique_district_values[district] = {}
                 processed_districts.add(district)

                 # Store the first non-null value found for this district
                 unique_district_values[district]['Medical'] = float(row.MedicalExpenses or 0.0)
                 unique_district_values[district]['Festival'] = float(row.FestivalAdvance or 0.0)
                 unique_district_values[district]['Swagram'] = float(row.SwagramMaharashtraDarshan or 0.0)
                 unique_district_values[district]['Other'] = float(row.Other or 0.0)

                 # Find the single non-null value among the 7th pay columns for this district
                 pay_diff_nps = float(row.SeventhPayCommissionDifferenceNPS or 0.0)
                 nps = float(row.NPS or 0.0)
                 pay_diff = float(row.SeventhPayCommissionDifference or 0.0)
                 # Assuming only one of these will have a value per district based on user description
                 # Summing available values (treating nulls as 0)
                 seventh_pay_combined = pay_diff_nps + nps + pay_diff
                 unique_district_values[district]['SeventhPayNPS'] = seventh_pay_combined


        # Sum the unique values across all processed districts
        for district in processed_districts:
            table3_totals['Medical'] += unique_district_values[district].get('Medical', 0.0)
            table3_totals['Festival'] += unique_district_values[district].get('Festival', 0.0)
            table3_totals['Swagram'] += unique_district_values[district].get('Swagram', 0.0)
            table3_totals['SeventhPayNPS'] += unique_district_values[district].get('SeventhPayNPS', 0.0)
            table3_totals['Other'] += unique_district_values[district].get('Other', 0.0)

        # Calculate final total expense
        table3_totals['Expense_Total'] = sum(table3_totals[k] for k in ['Medical', 'Festival', 'Swagram', 'SeventhPayNPS', 'Other'])

        # Prepare the single row for the template
        table3_final_data = [{
                "SrNo": 1,
                "Division": "कोकण विभाग",
                "Medical": int(round(table3_totals['Medical'])), # Convert back to int/round as per example
                "Festival": int(round(table3_totals['Festival'])),
                "Swagram": int(round(table3_totals['Swagram'])),
                "SeventhPayNPS": int(round(table3_totals['SeventhPayNPS'])), # Key for template
                "Other": int(round(table3_totals['Other'])),
                "Expense_Total": int(round(table3_totals['Expense_Total']))
        }]

        logger.info(f"(Helper REVISED v3) Processed expense totals: {table3_final_data}")

        return {
            "table1_rows": table1_rows,
            "table1_totals": table1_totals,
            "table2_rows": table2_rows, # Now contains data from ApprovedPostTarget
            "table2_totals": table2_totals, # Calculated totals for table 2
            "table3_data": table3_final_data, # Use new calculation
        }

    except Exception as e:
        logger.error(f"(Helper REVISED v3) Error fetching/processing post expenses summary data: {e}", exc_info=True)
        return None
# --- END HELPER FUNCTION ---

# --- Main GET Route (Remains the same structure) ---
@router.get("", response_class=HTMLResponse)
async def ui_list_post_expenses(
    request: Request, db: Session = Depends(get_db), view: Optional[str] = Query("edit"),
    district: Optional[str] = Query(None), category: Optional[str] = Query(None),
    cls: Optional[str] = Query(None, alias="class")
):
    context = { "request": request, "resource_name": "Post Expenses", "districts": DISTRICTS,
                "categories": CATEGORIES, "classes": CLASSES_SHEET3, "current_district": district,
                "current_category": category, "current_class": cls, "view_mode": view }
    if view == "summary":
        logger.info("Requesting Post Expenses Summary view")
        summary_data = get_post_expenses_summary_data(db)
        if summary_data is None: raise HTTPException(status_code=500, detail="Could not generate Post Expenses summary data.")
        context["resource_name"] = "Post Expenses Summary"; context.update(summary_data)
        logger.info("Rendering Post Expenses Summary view")
        return templates.TemplateResponse("post_expenses_list.html", context)
    elif view == "edit":
        logger.info("Requesting Post Expenses List (edit) view")
        query = db.query(models.PostExpenses)
        if district: query = query.filter(models.PostExpenses.District == district)
        if category: query = query.filter(models.PostExpenses.Category == category)
        if cls: query = query.filter(models.PostExpenses.Class == cls)
        items = query.order_by(models.PostExpenses.id).all()
        filtered_params = {k: v for k, v in {"district": district, "category": category, "class": cls}.items() if v is not None}
        # Pass specific query string for list export
        context["export_query_string_list"] = "?" + urlencode(filtered_params) if filtered_params else ""
        context["items"] = items
        logger.info(f"Rendering Post Expenses List (edit) view with {len(items)} items.")
        return templates.TemplateResponse("post_expenses_list.html", context)
    else:
        raise HTTPException(status_code=400, detail="Invalid view parameter. Use 'edit' or 'summary'.")

# --- Edit Form GET Route ---
@router.get("/{id}/edit", response_class=HTMLResponse)
async def ui_edit_post_expense_form(request: Request, id: int, db: Session = Depends(get_db)):
    item = db.query(models.PostExpenses).filter(models.PostExpenses.id == id).first()
    if not item: raise HTTPException(status_code=404, detail=f"Post Expense with ID {id} not found")
    item_dict = {}
    for col in item.__table__.columns: item_dict[col.name] = getattr(item, col.name)
    for float_col in ["SeventhPayCommissionDifferenceNPS", "NPS", "SeventhPayCommissionDifference"]:
        value = getattr(item, float_col); item_dict[f"{float_col}_str"] = str(value) if value is not None else ""
    return templates.TemplateResponse("post_expenses_form.html", {"request": request, "districts": DISTRICTS, "categories": CATEGORIES, "classes": CLASSES_SHEET3, "item": item, "item_dict": item_dict, "resource_name": "Post Expenses"})

# --- Edit Form POST Route ---
@router.post("/{id}/edit", response_class=HTMLResponse)
async def ui_update_post_expense(
    request: Request, id: int, db: Session = Depends(get_db), Class: str = Form(...), Category: str = Form(...), District: str = Form(...),
    FilledPosts: Optional[int] = Form(None), VacantPosts: Optional[int] = Form(None), MedicalExpenses: Optional[int] = Form(None),
    FestivalAdvance: Optional[int] = Form(None), SwagramMaharashtraDarshan: Optional[int] = Form(None),
    SeventhPayCommissionDifferenceNPS_str: Optional[str] = Form(None), NPS_str: Optional[str] = Form(None),
    SeventhPayCommissionDifference_str: Optional[str] = Form(None), Other: Optional[int] = Form(None)
):
    db_item = db.query(models.PostExpenses).filter(models.PostExpenses.id == id).first()
    if not db_item: raise HTTPException(status_code=404, detail=f"Post Expense with ID {id} not found")
    update_data = { "Class": Class, "Category": Category, "District": District, "FilledPosts": FilledPosts, "VacantPosts": VacantPosts, "MedicalExpenses": MedicalExpenses, "FestivalAdvance": FestivalAdvance, "SwagramMaharashtraDarshan": SwagramMaharashtraDarshan, "Other": Other }
    try:
        update_data["SeventhPayCommissionDifferenceNPS"] = float(SeventhPayCommissionDifferenceNPS_str) if SeventhPayCommissionDifferenceNPS_str else None
        update_data["NPS"] = float(NPS_str) if NPS_str else None
        update_data["SeventhPayCommissionDifference"] = float(SeventhPayCommissionDifference_str) if SeventhPayCommissionDifference_str else None
    except (ValueError, TypeError) as e:
         logger.error(f"Error converting float string for Post Expense ID {id}: {e}")
         item_dict_re = {}; # Prepare dict for re-rendering form
         for col in db_item.__table__.columns: item_dict_re[col.name] = getattr(db_item, col.name)
         for float_col in ["SeventhPayCommissionDifferenceNPS", "NPS", "SeventhPayCommissionDifference"]: value = getattr(db_item, float_col); item_dict_re[f"{float_col}_str"] = str(value) if value is not None else ""
         return templates.TemplateResponse("post_expenses_form.html", {"request": request, "error": f"Invalid number format submitted: {e}", "districts": DISTRICTS, "categories": CATEGORIES, "classes": CLASSES_SHEET3, "item": db_item, "item_dict": item_dict_re, "resource_name": "Post Expenses"}, status_code=400)
    for key, value in update_data.items():
         if value is not None: setattr(db_item, key, value)
         elif key in ["SeventhPayCommissionDifferenceNPS", "NPS", "SeventhPayCommissionDifference"] and value is None: setattr(db_item, key, None)
    try:
        db.commit(); db.refresh(db_item)
        return RedirectResponse(url=router.url_path_for("ui_list_post_expenses") + "?view=edit", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        db.rollback(); logger.error(f"Failed to update Post Expense ID {id}: {e}", exc_info=True)
        item_dict_re = {}; # Prepare dict for re-rendering form
        for col in db_item.__table__.columns: item_dict_re[col.name] = getattr(db_item, col.name)
        for float_col in ["SeventhPayCommissionDifferenceNPS", "NPS", "SeventhPayCommissionDifference"]: value = getattr(db_item, float_col); item_dict_re[f"{float_col}_str"] = str(value) if value is not None else ""
        return templates.TemplateResponse("post_expenses_form.html", {"request": request, "error": f"Failed to update record: {e}", "districts": DISTRICTS, "categories": CATEGORIES, "classes": CLASSES_SHEET3, "item": db_item, "item_dict": item_dict_re, "resource_name": "Post Expenses"}, status_code=400)

# --- NEW Route to Handle Updates for Approved Post Targets (Table 2) ---
@router.post("/summary/update-approved-posts", response_class=RedirectResponse)
async def ui_update_approved_posts(request: Request, db: Session = Depends(get_db)):
    form_data = await request.form()
    logger.info(f"Received form data for updating approved posts: {form_data}")
    try:
        updated_count = 0
        for class_key in ['1', '2', '3', '4']:
            for category in ['Permanent', 'Temporary']:
                form_field_name = f"{category.lower()}_class{class_key}" # e.g., permanent_class1
                count_str = form_data.get(form_field_name)

                if count_str is not None:
                    try:
                        count = int(count_str)
                        if count < 0: count = 0 # Ensure non-negative

                        # Find existing record or create if not found (upsert logic)
                        target = db.query(models.ApprovedPostTarget).filter_by(class_key=class_key, category=category).first()
                        if target:
                            if target.approved_count != count:
                                target.approved_count = count
                                logger.info(f"Updating ApprovedPostTarget: Class={class_key}, Cat={category}, Count={count}")
                                updated_count += 1
                        else:
                            # Create new if doesn't exist (for initial population)
                            target = models.ApprovedPostTarget(class_key=class_key, category=category, approved_count=count)
                            db.add(target)
                            logger.info(f"Creating ApprovedPostTarget: Class={class_key}, Cat={category}, Count={count}")
                            updated_count +=1 # Count creations as updates for commit check

                    except (ValueError, TypeError):
                        logger.warning(f"Invalid count value received for {form_field_name}: '{count_str}'. Skipping.")
                        # Optionally: add user feedback about skipped invalid entries
                        pass # Skip this field

        if updated_count > 0:
             db.commit()
             logger.info(f"Successfully updated/created {updated_count} approved post target records.")
        else:
            logger.info("No changes detected in approved post targets.")

    except Exception as e:
        db.rollback()
        logger.error(f"Error updating approved post targets: {e}", exc_info=True)
        # How to provide feedback? Redirecting back might lose error context.
        # For now, just log and redirect. Consider flash messages if using a full framework.
    # Always redirect back to the summary view
    # Ensure the redirect URL is correct and matches the main GET route
    return RedirectResponse(url=router.url_path_for("ui_list_post_expenses") + "?view=summary", status_code=status.HTTP_303_SEE_OTHER)


# --- UPDATED Excel Download Route for Summary ---
@router.get("/summary/export-excel", response_class=StreamingResponse)
async def export_post_expenses_summary_excel(db: Session = Depends(get_db)):
    logger.info("--- Entered export_post_expenses_summary_excel ---")
    summary_data = get_post_expenses_summary_data(db)
    if summary_data is None: raise HTTPException(status_code=500, detail="Could not generate summary data for download.")
    try:
        logger.info("Preparing data for Post Expenses Summary Excel...")
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Sheet 1: Table 1 (Post Counts)
            df1_rows = pd.DataFrame(summary_data['table1_rows'])
            df1_totals = pd.DataFrame([summary_data['table1_totals']])
            df1 = pd.concat([df1_rows, df1_totals], ignore_index=True)
            df1.columns = ["अ.क्र.", "वर्ग", "स्थायी-भरलेली", "स्थायी-रिक्त", "अस्थायी-भरलेली", "अस्थायी-रिक्त", "एकूण पदे"]
            df1.to_excel(writer, sheet_name='Post Counts by Class', index=False)

            # Sheet 2: Table 2 (Approved Posts - Fetched from DB)
            df2_rows = pd.DataFrame(summary_data['table2_rows'])
            df2_totals = pd.DataFrame([summary_data['table2_totals']])
            df2 = pd.concat([df2_rows, df2_totals], ignore_index=True)
            # Select and rename columns for Excel sheet
            df2 = df2[['CadreLabel', 'Approved_Permanent', 'Approved_Temporary', 'Approved_Total']]
            df2.columns = ["संवर्ग", "मंजूर पदे-स्थायी", "मंजूर पदे-अस्थायी", "मंजूर पदे-एकूण"]
            df2.to_excel(writer, sheet_name='Approved Posts Summary', index=False)

            # Sheet 3: Table 3 (Expense Totals - Calculated)
            df3 = pd.DataFrame(summary_data['table3_data'])
            # Ensure column order matches the visual table
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

# --- Existing Excel Download Route for List View ---
@router.get("/list/export-excel", response_class=StreamingResponse)
async def export_post_expenses_list_excel(
    db: Session = Depends(get_db), district: Optional[str] = Query(None), category: Optional[str] = Query(None),
    cls: Optional[str] = Query(None, alias="class")
):
    # (Keep the existing logic for exporting the filtered list)
    logger.info("--- Entered export_post_expenses_LIST_excel ---")
    query = db.query(models.PostExpenses)
    if district: query = query.filter(models.PostExpenses.District == district)
    if category: query = query.filter(models.PostExpenses.Category == category)
    if cls: query = query.filter(models.PostExpenses.Class == cls)
    items = query.order_by(models.PostExpenses.id).all()
    data_dict_list = []
    if items:
        columns = [c.name for c in models.PostExpenses.__table__.columns]
        for item in items: data_dict_list.append({col: getattr(item, col, None) for col in columns})
    df = pd.DataFrame(data_dict_list)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Post Expenses List', index=False)
    output.seek(0)
    headers = {'Content-Disposition': 'attachment; filename="post_expenses_list.xlsx"'}
    return StreamingResponse(output, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
# --- End Excel ---