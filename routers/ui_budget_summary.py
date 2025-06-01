from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.responses import HTMLResponse
# Add StreamingResponse for file download
from starlette.responses import StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Any
import models  # Ensure models.py is in the same directory or PYTHONPATH
from database import get_db # Ensure database.py is in the same directory or PYTHONPATH
from collections import defaultdict
from config import POSITION_ORDER, POSITION_SORT_MAP # Ensure config.py is in the same directory or PYTHONPATH
import logging
# Add imports for Excel generation
import pandas as pd
import io

# --- Basic Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
# --- End Logging Setup ---

templates = Jinja2Templates(directory="templates")

router = APIRouter(
    prefix="/ui/budget-summary",
    tags=["UI - Budget Summary"],
    include_in_schema=False # Keep UI routes out of OpenAPI schema
)

# Define consistent keys for class aggregation (used internally)
CLASS_1_2_KEY = 'Class-1 & 2'
CLASS_3_KEY = 'Class-3'
CLASS_4_KEY = 'Class-4'
VALID_CLASS_KEYS = [CLASS_1_2_KEY, CLASS_3_KEY, CLASS_4_KEY]

# Marathi Labels for final summary table
CLASS_LABEL_MAP_MR = {
    CLASS_1_2_KEY: 'वर्ग-1 व 2',
    CLASS_3_KEY: 'वर्ग-3',
    CLASS_4_KEY: 'वर्ग-4'
}
CATEGORY_LABEL_MAP_MR = {
    'Permanent': 'स्थायी',
    'Temporary': 'अस्थायी'
}
TOTAL_CLASS_LABEL_MR = "वर्ग-1,2,3 व 4" # Label for the category total row class
GRAND_TOTAL_CATEGORY_LABEL_MR = "स्थायी + अस्थायी"

# --- Helper Function to Get Summary Data (REVISED for Marathi Labels in final summary) ---
def get_budget_summary_data(db: Session = Depends(get_db)) -> Dict[str, Any]:
    logger.info("--- (Helper) Fetching budget summary data (with Marathi labels) ---")
    try:
        # --- Database Query (Same as before) ---
        logger.info("(Helper) Attempting database query...")
        query = db.query(
            models.BudgetPostDetails.Category,
            models.BudgetPostDetails.Class,
            models.BudgetPostDetails.Designation,
            func.sum(models.BudgetPostDetails.SanctionedPosts202425).label("Sum_Sanctioned2425"),
            func.sum(models.BudgetPostDetails.SanctionedPosts202526).label("Sum_Sanctioned2526"),
            func.sum(models.BudgetPostDetails.SpecialPay).label("Sum_SpecialPay"),
            func.sum(models.BudgetPostDetails.BasicPay).label("Sum_BasicPay"),
            func.sum(models.BudgetPostDetails.GradePay).label("Sum_GradePay"),
            func.sum(models.BudgetPostDetails.DearnessAllowance64).label("Sum_DA64"),
            func.sum(models.BudgetPostDetails.LocalSupplemetoryAllowance).label("Sum_LocalSupplemetoryAllowance"),
            func.sum(models.BudgetPostDetails.LocalHRA).label("Sum_LocalHRA"),
            func.sum(models.BudgetPostDetails.VehicleAllowance).label("Sum_VehicleAllowance"),
            func.sum(models.BudgetPostDetails.WashingAllowance).label("Sum_WashingAllowance"),
            func.sum(models.BudgetPostDetails.CashAllowance).label("Sum_CashAllowance"),
            func.sum(models.BudgetPostDetails.FootWareAllowanceOther).label("Sum_FootWareAllowanceOther")
        ).group_by(
            models.BudgetPostDetails.Category,
            models.BudgetPostDetails.Class,
            models.BudgetPostDetails.Designation
        ).order_by(
            models.BudgetPostDetails.Category,
        ).all()
        logger.info(f"(Helper) Database query successful. Found {len(query)} rows.")
        # --- End Database Query ---

        # --- Initialization (Mostly same, using English keys internally for calculations) ---
        permanent_rows_unsorted = []
        temporary_rows_unsorted = []
        permanent_totals_detailed = defaultdict(int)
        temporary_totals_detailed = defaultdict(int)
        # Internal keys for calculations and data access in template loops for tables 1 & 2
        internal_col_keys = [
            "Approved Posts 2024-25", "Approved Posts 2025-26", "Special Pay", "Basic Pay", "Grade Pay",
            "Total Pay", "Dearness Allowance 64%", "Local Supplementary Allowance", "House Rent Allowance",
            "Vehicle Allowance", "Washing Allowance", "Cash Allowance", "Footwear Allowance / Others", "Total"
        ]
        for key in internal_col_keys:
            permanent_totals_detailed[key] = 0
            temporary_totals_detailed[key] = 0

        # For aggregating data for the final summary table before adding Marathi labels
        class_summary_agg = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
        # --- End Initialization ---

        # --- Data Processing Loop (Same as before) ---
        logger.info("(Helper) Starting data processing loop...")
        for i, row in enumerate(query):
            # Determine internal class key
            raw_class_value = (row.Class or "").strip()
            current_class_key = None
            if raw_class_value == CLASS_1_2_KEY: current_class_key = CLASS_1_2_KEY
            elif raw_class_value == CLASS_3_KEY: current_class_key = CLASS_3_KEY
            elif raw_class_value == CLASS_4_KEY: current_class_key = CLASS_4_KEY
            else:
                logger.warning(f"(Helper) Row {i}: Unexpected class value '{row.Class}' for Designation '{row.Designation}'. Skipping.")
                continue

            # Calculations
            special_pay = int(row.Sum_SpecialPay or 0)
            basic_pay = int(row.Sum_BasicPay or 0)
            grade_pay = int(row.Sum_GradePay or 0)
            total_pay = special_pay + basic_pay + grade_pay # Calculated Total Pay
            da_64 = int(row.Sum_DA64 or 0)
            local_supp_allowance = int(row.Sum_LocalSupplemetoryAllowance or 0)
            hra = int(row.Sum_LocalHRA or 0)
            vehicle_allowance = int(row.Sum_VehicleAllowance or 0)
            washing_allowance = int(row.Sum_WashingAllowance or 0)
            cash_allowance = int(row.Sum_CashAllowance or 0)
            footwear_others = int(row.Sum_FootWareAllowanceOther or 0)
            grand_total = ( # Calculated Grand Total
                total_pay + da_64 + local_supp_allowance + hra +
                vehicle_allowance + washing_allowance + cash_allowance + footwear_others
            )

            # Prepare row dictionary using internal English keys
            processed_row_detailed = {
                "Class": raw_class_value, # Keep original class for potential filtering if needed
                "Position": row.Designation,
                "Approved Posts 2024-25": int(row.Sum_Sanctioned2425 or 0),
                "Approved Posts 2025-26": int(row.Sum_Sanctioned2526 or 0),
                "Special Pay": special_pay,
                "Basic Pay": basic_pay,
                "Grade Pay": grade_pay,
                "Total Pay": total_pay, # Store calculated pay total
                "Dearness Allowance 64%": da_64,
                "Local Supplementary Allowance": local_supp_allowance,
                "House Rent Allowance": hra,
                "Vehicle Allowance": vehicle_allowance,
                "Washing Allowance": washing_allowance,
                "Cash Allowance": cash_allowance,
                "Footwear Allowance / Others": footwear_others,
                "Total": grand_total # Store calculated grand total
            }

            # Aggregate for the final class-wise summary table
            target_agg_dict = class_summary_agg[row.Category][current_class_key]
            for key in internal_col_keys: # Aggregate using internal keys
                target_agg_dict[key] += processed_row_detailed.get(key, 0)

            # Append to lists for individual tables (Permanent/Temporary) and update their totals
            if row.Category == 'Permanent':
                permanent_rows_unsorted.append(processed_row_detailed)
                for key in internal_col_keys: permanent_totals_detailed[key] += processed_row_detailed.get(key, 0)
            elif row.Category == 'Temporary':
                temporary_rows_unsorted.append(processed_row_detailed)
                for key in internal_col_keys: temporary_totals_detailed[key] += processed_row_detailed.get(key, 0)
        logger.info("(Helper) Data processing loop finished.")
        # --- End Data Processing Loop ---

        # --- Sorting (Same as before) ---
        logger.info("(Helper) Starting sorting...")
        def sort_key(row_dict):
            position = row_dict.get('Position')
            if position is None: return float('inf')
            return POSITION_SORT_MAP.get(position, float('inf'))

        permanent_rows_sorted = sorted(permanent_rows_unsorted, key=sort_key)
        temporary_rows_sorted = sorted(temporary_rows_unsorted, key=sort_key)
        logger.info("(Helper) Sorting finished.")
        # --- End Sorting ---

        # --- Final List Preparation (Add Sr No. AFTER sorting) ---
        permanent_rows_final = [{"Sr No.": i, **row} for i, row in enumerate(permanent_rows_sorted, 1)]
        temporary_rows_final = [{"Sr No.": i, **row} for i, row in enumerate(temporary_rows_sorted, 1)]

        # Prepare totals dicts for HTML rendering (still using internal keys for data)
        permanent_totals_render = {"Sr No.": "--", "Position": "एकूण", **permanent_totals_detailed} # Use Marathi label for Total Position
        temporary_totals_render = {"Sr No.": "--", "Position": "एकूण", **temporary_totals_detailed} # Use Marathi label for Total Position
        logger.info("(Helper) Final list preparation complete.")
        # --- End Final List Preparation ---

        # --- REVISED Final Summary Aggregation (Inject Marathi Labels) ---
        logger.info("(Helper) Starting final summary aggregation with Marathi labels...")
        final_summary_rows = []
        grand_totals_summary = defaultdict(int)
        # Use internal_col_keys which map to the calculated numeric values
        summary_numeric_keys = internal_col_keys

        for category_internal in ['Permanent', 'Temporary']:
            category_label_mr = CATEGORY_LABEL_MAP_MR.get(category_internal, category_internal)
            category_total_summary = {
                "CategoryLabel": category_label_mr,
                "ClassLabel": TOTAL_CLASS_LABEL_MR # Use Marathi total class label
            }

            # Add rows for each standard class key
            for cls_key_internal in VALID_CLASS_KEYS:
                cls_label_mr = CLASS_LABEL_MAP_MR.get(cls_key_internal, cls_key_internal)
                aggregated_data = class_summary_agg[category_internal].get(cls_key_internal, defaultdict(int))
                output_row = {
                    "CategoryLabel": category_label_mr,
                    "ClassLabel": cls_label_mr
                }
                for key in summary_numeric_keys: # Use internal keys to fetch data
                    value = aggregated_data.get(key, 0)
                    output_row[key] = value # Store with internal key
                final_summary_rows.append(output_row)

            # Add the total row for the category using pre-calculated detailed totals
            current_category_totals_detailed = permanent_totals_detailed if category_internal == 'Permanent' else temporary_totals_detailed
            for key in summary_numeric_keys: # Use internal keys
                value = current_category_totals_detailed.get(key, 0)
                category_total_summary[key] = value
                grand_totals_summary[key] += value # Add to overall grand total using internal key

            final_summary_rows.append(category_total_summary)


        # Grand total summary row (using totals calculated above)
        grand_total_row = {
            "CategoryLabel": GRAND_TOTAL_CATEGORY_LABEL_MR,
            "ClassLabel": "" # No specific class for grand total
        }
        for key in summary_numeric_keys: # Use internal keys
            grand_total_row[key] = grand_totals_summary.get(key, 0)
        final_summary_rows.append(grand_total_row)
        logger.info("(Helper) Final summary aggregation complete.")
        # --- End Final Summary Aggregation ---

        logger.info("(Helper) Successfully prepared summary data.")
        # Return all necessary pieces for both HTML and Excel
        return {
            "permanent_rows": permanent_rows_final,
            "temporary_rows": temporary_rows_final,
            "permanent_totals_render": permanent_totals_render, # Contains totals with internal keys
            "temporary_totals_render": temporary_totals_render, # Contains totals with internal keys
            "final_summary_rows": final_summary_rows, # Contains Marathi labels + data with internal keys
            "internal_col_keys_for_template": internal_col_keys # Pass internal keys for template iteration
        }

    except Exception as e:
         logger.error(f"(Helper) Error during data processing/sorting/aggregation: {e}", exc_info=True)
         return None # Indicate failure
# --- End Helper Function ---


# --- Route to Display HTML Page (No changes needed here, it just calls the helper) ---
@router.get("", response_class=HTMLResponse)
async def ui_budget_summary_report(request: Request, db: Session = Depends(get_db)):
    logger.info("--- Entered ui_budget_summary_report (HTML) ---")
    summary_data = get_budget_summary_data(db) # Call revised helper function

    if summary_data is None:
        logger.error("Failed to get summary data for HTML report.")
        raise HTTPException(status_code=500, detail="Could not generate summary data.")

    try:
        template_context = {
            "request": request,
            "resource_name": "अर्थसंकल्पीय अंदाजपत्रक सारांश", # Marathi Title
             # Pass all data directly from the helper's return dictionary
             **summary_data
        }
        logger.info("Attempting to render template budget_summary.html...")
        # Assuming this router points to a specific template, or uses the main one
        # If using budget_post_details_list.html, ensure view_mode is set correctly
        # This route seems standalone, so budget_summary.html is likely correct
        # If integrated with budget_post_details, call that route instead
        response = templates.TemplateResponse("budget_summary.html", template_context) # Or appropriate template name
        logger.info("Template rendering successful.")
        logger.info("--- Exiting ui_budget_summary_report (HTML) normally ---")
        return response
    except Exception as e:
         logger.error(f"Error during HTML template rendering: {e}", exc_info=True)
         raise HTTPException(status_code=500, detail=f"Template rendering error: {e}")
# --- End HTML Route ---


# --- Route to Download Excel File (No changes needed, uses internal keys) ---
@router.get("/download", response_class=StreamingResponse)
async def download_budget_summary_excel(db: Session = Depends(get_db)):
    logger.info("--- Entered download_budget_summary_excel ---")
    summary_data = get_budget_summary_data(db) # Call helper function

    if summary_data is None:
        logger.error("Failed to get summary data for Excel download.")
        raise HTTPException(status_code=500, detail="Could not generate summary data for download.")

    try:
        logger.info("Preparing data for Excel...")
        # Use data with internal English keys for DataFrames
        perm_df = pd.DataFrame(summary_data["permanent_rows"])
        temp_df = pd.DataFrame(summary_data["temporary_rows"])
        # Prepare final summary DF, mapping internal keys to desired column names if needed
        final_summary_data_for_df = []
        for row in summary_data["final_summary_rows"]:
            df_row = {
                "Category": row.get("CategoryLabel"), # Use Marathi label
                "Class": row.get("ClassLabel"),      # Use Marathi label
                **{key: row.get(key, 0) for key in summary_data.get("internal_col_keys_for_template", [])} # Get numeric data by internal key
            }
            final_summary_data_for_df.append(df_row)
        summary_df = pd.DataFrame(final_summary_data_for_df)


        # Define column order for excel (using internal keys where data exists)
        excel_col_order_detail = [
             "Sr No.", "Class", "Position", "Approved Posts 2024-25", "Approved Posts 2025-26",
             "Special Pay", "Basic Pay", "Grade Pay", "Total Pay", "Dearness Allowance 64%",
             "Local Supplementary Allowance", "House Rent Allowance", "Vehicle Allowance",
             "Washing Allowance", "Cash Allowance", "Footwear Allowance / Others", "Total"
        ]
        # Order for summary sheet - use keys present in the summary_df
        excel_col_order_summary = ["Category", "Class"] + summary_data.get("internal_col_keys_for_template", [])


        # Reorder columns if needed and if DFs are not empty
        if not perm_df.empty:
             # Ensure all columns exist before reordering
             cols_to_use = [col for col in excel_col_order_detail if col in perm_df.columns]
             perm_df = perm_df[cols_to_use]
        if not temp_df.empty:
             cols_to_use = [col for col in excel_col_order_detail if col in temp_df.columns]
             temp_df = temp_df[cols_to_use]
        if not summary_df.empty:
             # Ensure all columns exist before reordering
             cols_to_use = [col for col in excel_col_order_summary if col in summary_df.columns]
             summary_df = summary_df[cols_to_use]


        logger.info("Creating Excel file in memory...")
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            perm_df.to_excel(writer, sheet_name='Permanent Posts', index=False)
            temp_df.to_excel(writer, sheet_name='Temporary Posts', index=False)
            summary_df.to_excel(writer, sheet_name='Overall Summary', index=False)
        output.seek(0) # Go to the beginning of the stream

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
# --- End Excel Download Route ---