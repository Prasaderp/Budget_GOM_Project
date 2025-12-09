"""Service for post expenses summary data calculation"""
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from collections import defaultdict
from src.config import DCO_STAFF_IDENTIFIER
from src.utils_cache import ttl_cache
from ..repositories.post_expenses_repository import PostExpensesRepository
import logging

logger = logging.getLogger(__name__)


class PostExpensesSummaryService:
    """Service for calculating post expenses summary data"""
    
    def __init__(self, repository: PostExpensesRepository):
        """Initialize service with repository"""
        self.repository = repository
    
    @ttl_cache(ttl_seconds=180, use_global=True)
    def get_summary_data(
        self,
        fiscal_year: str = '2025-26',
        district: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get unified summary data for both district and overall post expenses
        
        Returns:
            Dict with table1_rows, table1_totals, table3_data
        """
        try:
            # Get post counts data
            post_counts_data = self.repository.get_summary_post_counts(
                fiscal_year=fiscal_year,
                district=district
            )
            
            # Get expense data
            expense_data = self.repository.get_summary_expense_data(
                fiscal_year=fiscal_year,
                district=district
            )
            
            # Process post counts into table1
            table1_data = defaultdict(lambda: defaultdict(int))
            for row in post_counts_data:
                cls = row.class_type
                cat = row.category
                if cls not in ['1', '2', '3', '4']:
                    continue
                table1_data[cls][f"{cat}_Filled"] = int(row.TotalFilled or 0)
                table1_data[cls][f"{cat}_Vacant"] = int(row.TotalVacant or 0)
            
            # Build table1 rows
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
                row_data["Row_Total"] = sum(row_data[k] for k in [
                    "Permanent_Filled", "Permanent_Vacant", 
                    "Temporary_Filled", "Temporary_Vacant"
                ])
                table1_rows.append(row_data)
                
                for key in [
                    "Permanent_Filled", "Permanent_Vacant", 
                    "Temporary_Filled", "Temporary_Vacant", "Row_Total"
                ]:
                    table1_totals[key] += row_data[key]
            
            table1_totals["SrNo"] = "--"
            table1_totals["Class"] = "एकूण"
            
            # Process expense data into table3
            table3_totals_dict = defaultdict(float)
            processed_districts = set()
            
            for row in expense_data:
                district_name = row.district
                if not district_name or district_name in processed_districts:
                    continue
                
                processed_districts.add(district_name)
                table3_totals_dict['Medical'] += float(row.medical_expenses or 0.0)
                table3_totals_dict['Festival'] += float(row.festival_advance or 0.0)
                table3_totals_dict['Swagram'] += float(row.swagram_maharashtra_darshan or 0.0)
                
                # Sum all NPS-related fields
                pay_diff_nps = float(row.seventh_pay_commission_difference_nps or 0.0)
                nps = float(row.nps or 0.0)
                pay_diff = float(row.seventh_pay_commission_difference or 0.0)
                table3_totals_dict['SeventhPayNPS'] += (pay_diff_nps + nps + pay_diff)
                
                table3_totals_dict['Other'] += float(row.other or 0.0)
            
            table3_totals_dict['Expense_Total'] = sum(table3_totals_dict[k] for k in [
                'Medical', 'Festival', 'Swagram', 'SeventhPayNPS', 'Other'
            ])
            
            division_label = district if district else "कोकण विभाग"
            table3_final_data_row = {
                "SrNo": 1,
                "Division": division_label,
                "Medical": int(round(table3_totals_dict['Medical'])),
                "Festival": int(round(table3_totals_dict['Festival'])),
                "Swagram": int(round(table3_totals_dict['Swagram'])),
                "SeventhPayNPS": int(round(table3_totals_dict['SeventhPayNPS'])),
                "Other": int(round(table3_totals_dict['Other'])),
                "Expense_Total": int(round(table3_totals_dict['Expense_Total']))
            }
            
            return {
                "table1_rows": table1_rows,
                "table1_totals": dict(table1_totals),
                "table3_data": [table3_final_data_row]
            }
        
        except Exception as e:
            logger.error(
                f"Error fetching/processing post expenses summary data (district={district}): {e}",
                exc_info=True
            )
            return None

