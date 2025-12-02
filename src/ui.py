import streamlit as st
import requests
import pandas as pd
from typing import Dict, Any, Optional
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import DISTRICTS, CATEGORIES, CLASSES_SHEET1_2, CLASSES_SHEET3, DESIGNATIONS, STATUSES, PRIMARY_UNITS

FASTAPI_BASE_URL = "http://127.0.0.1:8000"

def handle_response(response: requests.Response) -> Optional[Dict[str, Any]]:
    try:
        response.raise_for_status()
        if response.status_code == 204:
             st.success("Operation successful (No content returned).")
             return None
        if response.status_code in [200, 201]:
            return response.json()
    except requests.exceptions.HTTPError as http_err:
        st.error(f"HTTP error occurred: {http_err}")
        try:
            st.error(f"API Response: {response.json()}")
        except requests.exceptions.JSONDecodeError:
            st.error(f"API Response (non-JSON): {response.text}")
    except requests.exceptions.ConnectionError as conn_err:
        st.error(f"Connection error occurred: {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        st.error(f"Timeout error occurred: {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        st.error(f"An error occurred: {req_err}")
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
    return None


def api_get(endpoint: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    try:
        response = requests.get(f"{FASTAPI_BASE_URL}{endpoint}", params=params, timeout=10)
        return handle_response(response)
    except Exception as e:
        st.error(f"Error during GET request: {e}")
        return None


def api_post(endpoint: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    try:
        response = requests.post(f"{FASTAPI_BASE_URL}{endpoint}", json=data, timeout=10)
        return handle_response(response)
    except Exception as e:
        st.error(f"Error during POST request: {e}")
        return None


def api_put(endpoint: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    try:
        response = requests.put(f"{FASTAPI_BASE_URL}{endpoint}", json=data, timeout=10)
        return handle_response(response)
    except Exception as e:
        st.error(f"Error during PUT request: {e}")
        return None


def api_delete(endpoint: str) -> Optional[Dict[str, Any]]:
    try:
        response = requests.delete(f"{FASTAPI_BASE_URL}{endpoint}", timeout=10)
        return handle_response(response)

    except Exception as e:
        st.error(f"Error during DELETE request: {e}")
        return None

st.set_page_config(layout="wide")
st.title("GOM Project Database Interface")
st.sidebar.title("Navigation")
resource_options = [
    "Budget Post Details",
    "Post Status",
    "Post Expenses",
    "Unit Expenditure"
]
selected_resource = st.sidebar.radio("Select Resource:", resource_options)
if selected_resource == "Budget Post Details":
    st.header("Budget Post Details Management")
    base_endpoint = "/budget_post_details/"

    tab1, tab2, tab3 = st.tabs(["View All", "View/Update/Delete Single", "Create New"])

    with tab1:
        st.subheader("View All Budget Post Details")
        if st.button("Load All Details"):
            data = api_get(base_endpoint)
            if data is not None:
                if data:
                    df = pd.DataFrame(data)
                    st.dataframe(df)
                else:
                    st.info("No records found.")

    with tab2:
        st.subheader("View, Update, or Delete a Single Record")
        record_id_to_manage = st.number_input("Enter Record ID:", min_value=1, step=1, key="bpd_manage_id")

        if 'bpd_loaded_record' not in st.session_state:
            st.session_state.bpd_loaded_record = None

        col_load, col_delete = st.columns([1,1])
        with col_load:
            if st.button("Load Record", key="bpd_load"):
                if record_id_to_manage:
                    endpoint = f"{base_endpoint}{record_id_to_manage}"
                    record_data = api_get(endpoint)
                    if record_data:
                        st.session_state.bpd_loaded_record = record_data
                        st.success(f"Record ID {record_id_to_manage} loaded.")
                    else:
                        st.session_state.bpd_loaded_record = None
                else:
                    st.warning("Please enter a valid Record ID.")

        with col_delete:
             if st.button("Delete Record", key="bpd_delete"):
                if record_id_to_manage:
                    if st.checkbox(f"Confirm deletion of Record ID {record_id_to_manage}?", key="bpd_delete_confirm"):
                        endpoint = f"{base_endpoint}{record_id_to_manage}"
                        api_delete(endpoint) # Success/error messages handled inside
                        st.session_state.bpd_loaded_record = None # Clear loaded data after delete attempt
                else:
                    st.warning("Please enter a Record ID to delete.")


        if st.session_state.bpd_loaded_record:
            st.divider()
            st.subheader(f"Update Record ID: {st.session_state.bpd_loaded_record.get('id', 'N/A')}")
            current_data = st.session_state.bpd_loaded_record

            with st.form("update_bpd_form"):
                district = st.selectbox("District", DISTRICTS, index=DISTRICTS.index(current_data.get('District')) if current_data.get('District') in DISTRICTS else 0, key="bpd_update_district")
                category = st.selectbox("Category", CATEGORIES, index=CATEGORIES.index(current_data.get('Category')) if current_data.get('Category') in CATEGORIES else 0, key="bpd_update_category")
                cls = st.selectbox("Class", CLASSES_SHEET1_2, index=CLASSES_SHEET1_2.index(current_data.get('Class')) if current_data.get('Class') in CLASSES_SHEET1_2 else 0, key="bpd_update_class")
                designation = st.text_input("Designation", value=current_data.get('Designation', ''), key="bpd_update_designation")
                sanctioned_2425 = st.number_input("Sanctioned Posts 2024-25", min_value=0, step=1, value=current_data.get('SanctionedPosts202425', 0), key="bpd_update_sanc2425")
                sanctioned_2526 = st.number_input("Sanctioned Posts 2025-26", min_value=0, step=1, value=current_data.get('SanctionedPosts202526', 0), key="bpd_update_sanc2526")
                special_pay = st.number_input("Special Pay", min_value=0, step=1, value=current_data.get('SpecialPay', 0), key="bpd_update_specialpay")
                basic_pay = st.number_input("Basic Pay", min_value=0.0, step=0.1, value=float(current_data.get('BasicPay', 0)), key="bpd_update_basicpay")
                grade_pay = st.number_input("Grade Pay", min_value=0, step=1, value=current_data.get('GradePay', 0), key="bpd_update_gradepay")
                da_64 = st.number_input("Dearness Allowance 64%", min_value=0, step=1, value=current_data.get('DearnessAllowance64', 0), key="bpd_update_da64")
                local_supplemetory_allowance = st.number_input("Local Supplementary Allowance", min_value=0, step=1, value=current_data.get('LocalSupplemetoryAllowance', 0), key="bpd_update_localsupp")
                local_hra = st.number_input("Local HRA", min_value=0, step=1, value=current_data.get('LocalHRA', 0), key="bpd_update_localhra")
                vehicle_allowance = st.number_input("Vehicle Allowance", min_value=0, step=1, value=current_data.get('VehicleAllowance', 0), key="bpd_update_vehicle")
                washing_allowance = st.number_input("Washing Allowance", min_value=0, step=1, value=current_data.get('WashingAllowance', 0), key="bpd_update_washing")
                cash_allowance = st.number_input("Cash Allowance", min_value=0, step=1, value=current_data.get('CashAllowance', 0), key="bpd_update_cash")
                FootWareAllowanceOther = st.number_input("FootWareAllowanceOther", min_value=0, step=1, value=current_data.get('FootWareAllowanceOther', 0), key="bpd_update_FootWareAllowanceOther")

                submitted = st.form_submit_button("Update Record")
                if submitted:
                    update_payload = {
                        "District": district,
                        "Category": category,
                        "Class": cls,
                        "Designation": designation,
                        "SanctionedPosts202425": sanctioned_2425,
                        "SanctionedPosts202526": sanctioned_2526,
                        "SpecialPay": special_pay,
                        "BasicPay": basic_pay,
                        "GradePay": grade_pay,
                        "DearnessAllowance64": da_64,
                        "LocalSupplemetoryAllowance" : local_supplemetory_allowance,
                        "LocalHRA": local_hra,
                        "VehicleAllowance": vehicle_allowance,
                        "WashingAllowance": washing_allowance,
                        "CashAllowance": cash_allowance,
                        "FootWareAllowanceOther": FootWareAllowanceOther
                    }
                    endpoint = f"{base_endpoint}{record_id_to_manage}"
                    updated_record = api_put(endpoint, data=update_payload)
                    if updated_record:
                        st.success("Record updated successfully!")
                        st.json(updated_record)
                        st.session_state.bpd_loaded_record = updated_record # Update loaded data


    with tab3:
        st.subheader("Create a New Budget Post Detail")
        with st.form("create_bpd_form"):
            st.info("Fields marked with * are mandatory for creation based on API schema.")
            district = st.selectbox("District *", DISTRICTS, key="bpd_create_district")
            category = st.selectbox("Category *", CATEGORIES, key="bpd_create_category")
            cls = st.selectbox("Class *", CLASSES_SHEET1_2, key="bpd_create_class")
            designation = st.text_input("Designation *", key="bpd_create_designation")
            sanctioned_2425 = st.number_input("Sanctioned Posts 2024-25", min_value=0, step=1, value=0, key="bpd_create_sanc2425")
            sanctioned_2526 = st.number_input("Sanctioned Posts 2025-26", min_value=0, step=1, value=0, key="bpd_create_sanc2526")
            special_pay = st.number_input("Special Pay", min_value=0, step=1, value=0, key="bpd_create_specialpay")
            basic_pay = st.number_input("Basic Pay", min_value=0.0, step=0.1, value=0.0, key="bpd_create_basicpay")
            grade_pay = st.number_input("Grade Pay", min_value=0, step=1, value=0, key="bpd_create_gradepay")
            da_64 = st.number_input("Dearness Allowance 64%", min_value=0, step=1, value=0, key="bpd_create_da64")
            local_supplemetory_allowance = st.number_input("Local Supplementary Allowance", min_value=0, step=1, value=0, key="bpd_create_localsupp")
            local_hra = st.number_input("Local HRA", min_value=0, step=1, value=0, key="bpd_create_localhra")
            vehicle_allowance = st.number_input("Vehicle Allowance", min_value=0, step=1, value=0, key="bpd_create_vehicle")
            washing_allowance = st.number_input("Washing Allowance", min_value=0, step=1, value=0, key="bpd_create_washing")
            cash_allowance = st.number_input("Cash Allowance", min_value=0, step=1, value=0, key="bpd_create_cash")
            other = st.number_input("Other", min_value=0, step=1, value=0, key="bpd_create_other")

            submitted = st.form_submit_button("Create Record")
            if submitted:
                if not all([district, category, cls, designation]):
                     st.error("Please fill in all mandatory fields marked with *.")
                else:
                    create_payload = {
                        "District": district,
                        "Category": category,
                        "Class": cls,
                        "Designation": designation,
                        "SanctionedPosts202425": sanctioned_2425,
                        "SanctionedPosts202526": sanctioned_2526,
                        "ExistingPay": special_pay,
                        "BasicPay": basic_pay,
                        "GradePay": grade_pay,
                        "DearnessAllowance64": da_64,
                        "LocalSupplemetoryAllowance" : local_supplemetory_allowance,
                        "LocalHRA": local_hra,
                        "VehicleAllowance": vehicle_allowance,
                        "WashingAllowance": washing_allowance,
                        "CashAllowance": cash_allowance,
                        "Other": other
                    }
                    created_record = api_post(base_endpoint, data=create_payload)
                    if created_record:
                        st.success("Record created successfully!")
                        st.json(created_record)
elif selected_resource == "Post Status":
    st.header("Post Status Management")
    base_endpoint = "/post_status/"

    tab1, tab2, tab3 = st.tabs(["View All", "View/Update/Delete Single", "Create New"])

    with tab1:
        st.subheader("View All Post Status Records")
        if st.button("Load All Status Records"):
             data = api_get(base_endpoint)
             if data is not None:
                 if data:
                     df = pd.DataFrame(data)
                     st.dataframe(df)
                 else:
                     st.info("No records found.")

    with tab2:
        st.subheader("View, Update, or Delete a Single Record")
        record_id_to_manage = st.number_input("Enter Record ID:", min_value=1, step=1, key="ps_manage_id")

        if 'ps_loaded_record' not in st.session_state:
            st.session_state.ps_loaded_record = None

        col_load, col_delete = st.columns([1,1])
        with col_load:
             if st.button("Load Record", key="ps_load"):
                 if record_id_to_manage:
                     endpoint = f"{base_endpoint}{record_id_to_manage}"
                     record_data = api_get(endpoint)
                     if record_data:
                         st.session_state.ps_loaded_record = record_data
                         st.success(f"Record ID {record_id_to_manage} loaded.")
                     else:
                         st.session_state.ps_loaded_record = None
                 else:
                     st.warning("Please enter a valid Record ID.")

        with col_delete:
             if st.button("Delete Record", key="ps_delete"):
                 if record_id_to_manage:
                     if st.checkbox(f"Confirm deletion of Record ID {record_id_to_manage}?", key="ps_delete_confirm"):
                         endpoint = f"{base_endpoint}{record_id_to_manage}"
                         api_delete(endpoint)
                         st.session_state.ps_loaded_record = None
                 else:
                     st.warning("Please enter a Record ID to delete.")

        if st.session_state.ps_loaded_record:
            st.divider()
            st.subheader(f"Update Record ID: {st.session_state.ps_loaded_record.get('id', 'N/A')}")
            current_data = st.session_state.ps_loaded_record

            with st.form("update_ps_form"):
                district = st.selectbox("District", DISTRICTS, index=DISTRICTS.index(current_data.get('District')) if current_data.get('District') in DISTRICTS else 0, key="ps_update_district")
                category = st.selectbox("Category", CATEGORIES, index=CATEGORIES.index(current_data.get('Category')) if current_data.get('Category') in CATEGORIES else 0, key="ps_update_category")
                cls = st.selectbox("Class", CLASSES_SHEET1_2, index=CLASSES_SHEET1_2.index(current_data.get('Class')) if current_data.get('Class') in CLASSES_SHEET1_2 else 0, key="ps_update_class")
                status = st.selectbox("Status", STATUSES, index=STATUSES.index(current_data.get('Status')) if current_data.get('Status') in STATUSES else 0, key="ps_update_status")
                posts = st.number_input("Posts", min_value=0, step=1, value=current_data.get('Posts', 0), key="ps_update_posts")
                salary = st.number_input("Salary", min_value=0, step=1, value=current_data.get('Salary', 0), key="ps_update_salary")
                grade_pay = st.number_input("Grade Pay", min_value=0, step=1, value=current_data.get('GradePay', 0), key="ps_update_gradepay")
                dearness_allowance = st.number_input("Dearness Allowance", min_value=0, step=1, value=current_data.get('DearnessAllowance', 0), key="ps_update_da")
                local_supp_allowance = st.number_input("Local Supplementary Allowance", min_value=0, step=1, value=current_data.get('LocalSupplemetoryAllowance', 0), key="ps_update_localsupp")
                house_rent_allowance = st.number_input("House Rent Allowance", min_value=0, step=1, value=current_data.get('HouseRentAllowance', 0), key="ps_update_hra")
                travel_allowance = st.number_input("Travel Allowance", min_value=0, step=1, value=current_data.get('TravelAllowance', 0), key="ps_update_travel")
                other = st.number_input("Other", min_value=0, step=1, value=current_data.get('Other', 0), key="ps_update_other")

                submitted = st.form_submit_button("Update Record")
                if submitted:
                    update_payload = {
                        "District": district,
                        "Category": category,
                        "Class": cls,
                        "Status": status,
                        "Posts": posts,
                        "Salary": salary,
                        "GradePay": grade_pay,
                        "DearnessAllowance": dearness_allowance,
                        "LocalSupplemetoryAllowance": local_supp_allowance,
                        "HouseRentAllowance": house_rent_allowance,
                        "TravelAllowance": travel_allowance,
                        "Other": other
                    }
                    endpoint = f"{base_endpoint}{record_id_to_manage}"
                    updated_record = api_put(endpoint, data=update_payload)
                    if updated_record:
                         st.success("Record updated successfully!")
                         st.json(updated_record)
                         st.session_state.ps_loaded_record = updated_record

    with tab3:
        st.subheader("Create a New Post Status Record")
        with st.form("create_ps_form"):
            st.info("Fields marked with * are mandatory for creation based on API schema.")
            district = st.selectbox("District *", DISTRICTS, key="ps_create_district")
            category = st.selectbox("Category *", CATEGORIES, key="ps_create_category")
            cls = st.selectbox("Class *", CLASSES_SHEET1_2, key="ps_create_class") # Assuming Sheet 1/2 classes
            status = st.selectbox("Status *", STATUSES, key="ps_create_status")
            posts = st.number_input("Posts", min_value=0, step=1, value=0, key="ps_create_posts")
            salary = st.number_input("Salary", min_value=0, step=1, value=0, key="ps_create_salary")
            grade_pay = st.number_input("Grade Pay", min_value=0, step=1, value=0, key="ps_create_gradepay")
            dearness_allowance = st.number_input("Dearness Allowance", min_value=0, step=1, value=0, key="ps_create_da")
            local_supp_allowance = st.number_input("Local Supplementary Allowance", min_value=0, step=1, value=0, key="ps_create_localsupp")
            house_rent_allowance = st.number_input("House Rent Allowance", min_value=0, step=1, value=0, key="ps_create_hra")
            travel_allowance = st.number_input("Travel Allowance", min_value=0, step=1, value=0, key="ps_create_travel")
            other = st.number_input("Other", min_value=0, step=1, value=0, key="ps_create_other")

            submitted = st.form_submit_button("Create Record")
            if submitted:
                if not all ([district, category, cls, status]):
                    st.error("Please fill in all mandatory fields marked with *.")
                else:
                    create_payload = {
                        "District": district,
                        "Category": category,
                        "Class": cls,
                        "Status": status,
                        "Posts": posts,
                        "Salary": salary,
                        "GradePay": grade_pay,
                        "DearnessAllowance": dearness_allowance,
                        "LocalSupplemetoryAllowance": local_supp_allowance,
                        "HouseRentAllowance": house_rent_allowance,
                        "TravelAllowance": travel_allowance,
                        "Other": other
                    }
                    created_record = api_post(base_endpoint, data=create_payload)
                    if created_record:
                        st.success("Record created successfully!")
                        st.json(created_record)


elif selected_resource == "Post Expenses":
    st.header("Post Expenses Management")
    base_endpoint = "/post_expenses/"

    tab1, tab2, tab3 = st.tabs(["View All", "View/Update/Delete Single", "Create New"])

    with tab1:
        st.subheader("View All Post Expenses Records")
        if st.button("Load All Expense Records"):
             data = api_get(base_endpoint)
             if data is not None:
                 if data:
                     df = pd.DataFrame(data)
                     st.dataframe(df)
                 else:
                     st.info("No records found.")

    with tab2:
        st.subheader("View, Update, or Delete a Single Record")
        record_id_to_manage = st.number_input("Enter Record ID:", min_value=1, step=1, key="pe_manage_id")

        if 'pe_loaded_record' not in st.session_state:
            st.session_state.pe_loaded_record = None

        col_load, col_delete = st.columns([1,1])
        with col_load:
             if st.button("Load Record", key="pe_load"):
                 if record_id_to_manage:
                     endpoint = f"{base_endpoint}{record_id_to_manage}"
                     record_data = api_get(endpoint)
                     if record_data:
                         st.session_state.pe_loaded_record = record_data
                         st.success(f"Record ID {record_id_to_manage} loaded.")
                     else:
                         st.session_state.pe_loaded_record = None
                 else:
                     st.warning("Please enter a valid Record ID.")

        with col_delete:
             if st.button("Delete Record", key="pe_delete"):
                 if record_id_to_manage:
                     if st.checkbox(f"Confirm deletion of Record ID {record_id_to_manage}?", key="pe_delete_confirm"):
                         endpoint = f"{base_endpoint}{record_id_to_manage}"
                         api_delete(endpoint)
                         st.session_state.pe_loaded_record = None
                 else:
                     st.warning("Please enter a Record ID to delete.")

        if st.session_state.pe_loaded_record:
            st.divider()
            st.subheader(f"Update Record ID: {st.session_state.pe_loaded_record.get('id', 'N/A')}")
            current_data = st.session_state.pe_loaded_record

            with st.form("update_pe_form"):
                cls = st.selectbox("Class", CLASSES_SHEET3, index=CLASSES_SHEET3.index(current_data.get('Class')) if current_data.get('Class') in CLASSES_SHEET3 else 0, key="pe_update_class")
                category = st.selectbox("Category", CATEGORIES, index=CATEGORIES.index(current_data.get('Category')) if current_data.get('Category') in CATEGORIES else 0, key="pe_update_category")
                district = st.selectbox("District", DISTRICTS, index=DISTRICTS.index(current_data.get('District')) if current_data.get('District') in DISTRICTS else 0, key="pe_update_district")
                filled_posts = st.number_input("Filled Posts", min_value=0, step=1, value=current_data.get('FilledPosts', 0), key="pe_update_filled")
                vacant_posts = st.number_input("Vacant Posts", min_value=0, step=1, value=current_data.get('VacantPosts', 0), key="pe_update_vacant")
                medical_expenses = st.number_input("Medical Expenses", min_value=0, step=1, value=current_data.get('MedicalExpenses', 0), key="pe_update_medical")
                festival_advance = st.number_input("Festival Advance", min_value=0, step=1, value=current_data.get('FestivalAdvance', 0), key="pe_update_festival")
                swagram = st.number_input("Swagram Maharashtra Darshan", min_value=0, step=1, value=current_data.get('SwagramMaharashtraDarshan', 0), key="pe_update_swagram")
                seventh_nps = st.number_input("7th Pay Commission Diff NPS", value=float(current_data.get('SeventhPayCommissionDifferenceNPS', 0.0)), format="%.2f", key="pe_update_7thnps")
                nps = st.number_input("NPS", value=float(current_data.get('NPS', 0.0)), format="%.2f", key="pe_update_nps")
                seventh_diff = st.number_input("7th Pay Commission Diff", value=float(current_data.get('SeventhPayCommissionDifference', 0.0)), format="%.2f", key="pe_update_7thdiff")
                other = st.number_input("Other", min_value=0, step=1, value=current_data.get('Other', 0), key="pe_update_other")

                submitted = st.form_submit_button("Update Record")
                if submitted:
                    update_payload = {
                        "Class": cls,
                        "Category": category,
                        "FilledPosts": filled_posts,
                        "VacantPosts": vacant_posts,
                        "District": district,
                        "MedicalExpenses": medical_expenses,
                        "FestivalAdvance": festival_advance,
                        "SwagramMaharashtraDarshan": swagram,
                        "SeventhPayCommissionDifferenceNPS": seventh_nps,
                        "NPS": nps,
                        "SeventhPayCommissionDifference": seventh_diff,
                        "Other": other
                    }
                    endpoint = f"{base_endpoint}{record_id_to_manage}"
                    updated_record = api_put(endpoint, data=update_payload)
                    if updated_record:
                         st.success("Record updated successfully!")
                         st.json(updated_record)
                         st.session_state.pe_loaded_record = updated_record


    with tab3:
        st.subheader("Create a New Post Expense Record")
        with st.form("create_pe_form"):
            st.info("Fields marked with * are mandatory for creation based on API schema.")
            cls = st.selectbox("Class *", CLASSES_SHEET3, key="pe_create_class") # Sheet 3 classes
            category = st.selectbox("Category *", CATEGORIES, key="pe_create_category")
            district = st.selectbox("District *", DISTRICTS, key="pe_create_district")
            filled_posts = st.number_input("Filled Posts", min_value=0, step=1, value=0, key="pe_create_filled")
            vacant_posts = st.number_input("Vacant Posts", min_value=0, step=1, value=0, key="pe_create_vacant")
            medical_expenses = st.number_input("Medical Expenses", min_value=0, step=1, value=0, key="pe_create_medical")
            festival_advance = st.number_input("Festival Advance", min_value=0, step=1, value=0, key="pe_create_festival")
            swagram = st.number_input("Swagram Maharashtra Darshan", min_value=0, step=1, value=0, key="pe_create_swagram")
            seventh_nps = st.number_input("7th Pay Commission Diff NPS", value=0.0, format="%.2f", key="pe_create_7thnps")
            nps = st.number_input("NPS", value=0.0, format="%.2f", key="pe_create_nps")
            seventh_diff = st.number_input("7th Pay Commission Diff", value=0.0, format="%.2f", key="pe_create_7thdiff")
            other = st.number_input("Other", min_value=0, step=1, value=0, key="pe_create_other")

            submitted = st.form_submit_button("Create Record")
            if submitted:
                 if not all ([cls, category, district]):
                     st.error("Please fill in all mandatory fields marked with *.")
                 else:
                    create_payload = {
                        "Class": cls,
                        "Category": category,
                        "FilledPosts": filled_posts,
                        "VacantPosts": vacant_posts,
                        "District": district,
                        "MedicalExpenses": medical_expenses,
                        "FestivalAdvance": festival_advance,
                        "SwagramMaharashtraDarshan": swagram,
                        "SeventhPayCommissionDifferenceNPS": seventh_nps,
                        "NPS": nps,
                        "SeventhPayCommissionDifference": seventh_diff,
                        "Other": other
                    }
                    created_record = api_post(base_endpoint, data=create_payload)
                    if created_record:
                        st.success("Record created successfully!")
                        st.json(created_record)


elif selected_resource == "Unit Expenditure":
    st.header("Unit Expenditure Management")
    base_endpoint = "/unit_expenditure/"

    tab1, tab2, tab3 = st.tabs(["View All", "View/Update/Delete Single", "Create New"])

    with tab1:
        st.subheader("View All Unit Expenditure Records")
        if st.button("Load All Expenditure Records"):
             data = api_get(base_endpoint)
             if data is not None:
                 if data:
                     df = pd.DataFrame(data)
                     st.dataframe(df)
                 else:
                     st.info("No records found.")

    with tab2:
        st.subheader("View, Update, or Delete a Single Record")
        record_id_to_manage = st.number_input("Enter Record ID:", min_value=1, step=1, key="ue_manage_id")

        if 'ue_loaded_record' not in st.session_state:
            st.session_state.ue_loaded_record = None

        col_load, col_delete = st.columns([1,1])
        with col_load:
             if st.button("Load Record", key="ue_load"):
                 if record_id_to_manage:
                     endpoint = f"{base_endpoint}{record_id_to_manage}"
                     record_data = api_get(endpoint)
                     if record_data:
                         st.session_state.ue_loaded_record = record_data
                         st.success(f"Record ID {record_id_to_manage} loaded.")
                     else:
                         st.session_state.ue_loaded_record = None
                 else:
                     st.warning("Please enter a valid Record ID.")

        with col_delete:
             if st.button("Delete Record", key="ue_delete"):
                 if record_id_to_manage:
                     if st.checkbox(f"Confirm deletion of Record ID {record_id_to_manage}?", key="ue_delete_confirm"):
                         endpoint = f"{base_endpoint}{record_id_to_manage}"
                         api_delete(endpoint)
                         st.session_state.ue_loaded_record = None
                 else:
                     st.warning("Please enter a Record ID to delete.")

        if st.session_state.ue_loaded_record:
            st.divider()
            st.subheader(f"Update Record ID: {st.session_state.ue_loaded_record.get('id', 'N/A')}")
            current_data = st.session_state.ue_loaded_record

            with st.form("update_ue_form"):
                primary_unit = st.selectbox("Primary/Secondary Units Of Account", PRIMARY_UNITS, index=PRIMARY_UNITS.index(current_data.get('PrimaryAndSecondaryUnitsOfAccount')) if current_data.get('PrimaryAndSecondaryUnitsOfAccount') in PRIMARY_UNITS else 0, key="ue_update_primary")
                district = st.selectbox("District", DISTRICTS, index=DISTRICTS.index(current_data.get('District')) if current_data.get('District') in DISTRICTS else 0, key="ue_update_district")
                actual_2122 = st.number_input("Actual Expenditure 2021-2022", min_value=0, step=1, value=current_data.get('ActualAmountExpenditure20212022', 0), key="ue_update_actual2122")
                actual_2223 = st.number_input("Actual Expenditure 2022-2023", min_value=0, step=1, value=current_data.get('ActualAmountExpenditure20222023', 0), key="ue_update_actual2223")
                actual_2324 = st.number_input("Actual Expenditure 2023-2024", min_value=0, step=1, value=current_data.get('ActualAmountExpenditure20232024', 0), key="ue_update_actual2324")
                budget_est_2425 = st.number_input("Budgetary Estimates 2024-2025", min_value=0, step=1, value=current_data.get('BudgetaryEstimates20242025', 0), key="ue_update_budget2425")
                improved_fc_2425 = st.number_input("Improved Forecast 2024-2025", min_value=0, step=1, value=current_data.get('ImprovedForecast20242025', 0), key="ue_update_improve2425")
                budget_est_2526_est = st.number_input("Budgetary Estimates 2025-2026 (Estimating Officer)", min_value=0, step=1, value=current_data.get('BudgetaryEstimates20252026EstimatingOfficer', 0), key="ue_update_budget2526est")
                budget_est_2526_ctrl = st.number_input("Budgetary Estimates 2025-2026 (Controlling Officer)", min_value=0, step=1, value=current_data.get('BudgetaryEstimates20252026ControllingOfficer', 0), key="ue_update_budget2526ctrl")
                budget_est_2526_admin = st.number_input("Budgetary Estimates 2025-2026 (Admin Dept)", min_value=0, step=1, value=current_data.get('BudgetaryEstimates20252026AdministrativeDepartment', 0), key="ue_update_budget2526admin")
                budget_est_2526_fin = st.number_input("Budgetary Estimates 2025-2026 (Finance Dept)", min_value=0, step=1, value=current_data.get('BudgetaryEstimates20252026FinanceDepartment', 0), key="ue_update_budget2526fin")

                submitted = st.form_submit_button("Update Record")
                if submitted:
                    update_payload = {
                        "PrimaryAndSecondaryUnitsOfAccount": primary_unit,
                        "District": district,
                        "ActualAmountExpenditure20212022": actual_2122,
                        "ActualAmountExpenditure20222023": actual_2223,
                        "ActualAmountExpenditure20232024": actual_2324,
                        "BudgetaryEstimates20242025": budget_est_2425,
                        "ImprovedForecast20242025": improved_fc_2425,
                        "BudgetaryEstimates20252026EstimatingOfficer": budget_est_2526_est,
                        "BudgetaryEstimates20252026ControllingOfficer": budget_est_2526_ctrl,
                        "BudgetaryEstimates20252026AdministrativeDepartment": budget_est_2526_admin,
                        "BudgetaryEstimates20252026FinanceDepartment": budget_est_2526_fin
                    }
                    endpoint = f"{base_endpoint}{record_id_to_manage}"
                    updated_record = api_put(endpoint, data=update_payload)
                    if updated_record:
                         st.success("Record updated successfully!")
                         st.json(updated_record)
                         st.session_state.ue_loaded_record = updated_record

    with tab3:
        st.subheader("Create a New Unit Expenditure Record")
        with st.form("create_ue_form"):
            st.info("Fields marked with * are mandatory for creation based on API schema.")
            primary_unit = st.selectbox("Primary/Secondary Units Of Account *", PRIMARY_UNITS, key="ue_create_primary")
            district = st.selectbox("District *", DISTRICTS, key="ue_create_district")
            actual_2122 = st.number_input("Actual Expenditure 2021-2022", min_value=0, step=1, value=0, key="ue_create_actual2122")
            actual_2223 = st.number_input("Actual Expenditure 2022-2023", min_value=0, step=1, value=0, key="ue_create_actual2223")
            actual_2324 = st.number_input("Actual Expenditure 2023-2024", min_value=0, step=1, value=0, key="ue_create_actual2324")
            budget_est_2425 = st.number_input("Budgetary Estimates 2024-2025", min_value=0, step=1, value=0, key="ue_create_budget2425")
            improved_fc_2425 = st.number_input("Improved Forecast 2024-2025", min_value=0, step=1, value=0, key="ue_create_improve2425")
            budget_est_2526_est = st.number_input("Budgetary Estimates 2025-2026 (Estimating Officer)", min_value=0, step=1, value=0, key="ue_create_budget2526est")
            budget_est_2526_ctrl = st.number_input("Budgetary Estimates 2025-2026 (Controlling Officer)", min_value=0, step=1, value=0, key="ue_create_budget2526ctrl")
            budget_est_2526_admin = st.number_input("Budgetary Estimates 2025-2026 (Admin Dept)", min_value=0, step=1, value=0, key="ue_create_budget2526admin")
            budget_est_2526_fin = st.number_input("Budgetary Estimates 2025-2026 (Finance Dept)", min_value=0, step=1, value=0, key="ue_create_budget2526fin")

            submitted = st.form_submit_button("Create Record")
            if submitted:
                 if not all ([primary_unit, district]):
                     st.error("Please fill in all mandatory fields marked with *.")
                 else:
                    create_payload = {
                        "PrimaryAndSecondaryUnitsOfAccount": primary_unit,
                        "District": district,
                        "ActualAmountExpenditure20212022": actual_2122,
                        "ActualAmountExpenditure20222023": actual_2223,
                        "ActualAmountExpenditure20232024": actual_2324,
                        "BudgetaryEstimates20242025": budget_est_2425,
                        "ImprovedForecast20242025": improved_fc_2425,
                        "BudgetaryEstimates20252026EstimatingOfficer": budget_est_2526_est,
                        "BudgetaryEstimates20252026ControllingOfficer": budget_est_2526_ctrl,
                        "BudgetaryEstimates20252026AdministrativeDepartment": budget_est_2526_admin,
                        "BudgetaryEstimates20252026FinanceDepartment": budget_est_2526_fin
                    }
                    created_record = api_post(base_endpoint, data=create_payload)
                    if created_record:
                        st.success("Record created successfully!")
                        st.json(created_record)

