"""Service for post expenses Excel export"""
from sqlalchemy.orm import Session
from typing import Optional
from fastapi.responses import StreamingResponse
from io import BytesIO
import pandas as pd
import logging

from ..repositories.post_expenses_repository import PostExpensesRepository
from .summary_service import PostExpensesSummaryService
from ...excel_export import export_original_workbook

logger = logging.getLogger(__name__)


class PostExpensesExportService:
    """Service for post expenses export operations"""
    
    def __init__(self, repository: PostExpensesRepository, summary_service: PostExpensesSummaryService):
        """Initialize service with repository and summary service"""
        self.repository = repository
        self.summary_service = summary_service
    
    def export_summary_excel(
        self,
        fiscal_year: str
    ) -> StreamingResponse:
        """
        Export summary data to Excel
        
        Returns:
            StreamingResponse with Excel file
        """
        try:
            summary_data = self.summary_service.get_summary_data(fiscal_year=fiscal_year)
            if summary_data is None:
                raise ValueError("Could not generate summary data for download.")
            
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                # Sheet 1: Post Counts by Class
                df1_rows = pd.DataFrame(summary_data['table1_rows'])
                df1_totals = pd.DataFrame([summary_data['table1_totals']])
                df1 = pd.concat([df1_rows, df1_totals], ignore_index=True)
                df1.columns = [
                    "अ.क्र.", "वर्ग", "स्थायी-भरलेली", "स्थायी-रिक्त",
                    "अस्थायी-भरलेली", "अस्थायी-रिक्त", "एकूण पदे"
                ]
                df1.to_excel(writer, sheet_name='Post Counts by Class', index=False)
                
                # Sheet 2: Expense Summary
                df3 = pd.DataFrame(summary_data['table3_data'])
                df3 = df3[[
                    'SrNo', 'Division', 'Medical', 'Festival', 'Swagram',
                    'SeventhPayNPS', 'Other', 'Expense_Total'
                ]]
                df3.columns = [
                    "अ.क्र.", "जिल्हा / विभाग", "वैद्यकिय खर्च",
                    "उत्सव/सण अग्रिम", "स्वग्राम/महाराष्ट्र दर्शन",
                    "7 व्या वेतन आयोग फरक+ NPS", "इतर", "एकूण खर्च"
                ]
                df3.to_excel(writer, sheet_name='Expense Summary', index=False)
            
            output.seek(0)
            headers = {'Content-Disposition': 'attachment; filename="post_expenses_summary_report.xlsx"'}
            return StreamingResponse(
                output,
                headers=headers,
                media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
        except Exception as e:
            logger.error(f"Failed to generate Post Expenses Summary Excel file: {e}", exc_info=True)
            raise ValueError(f"Could not generate Excel file: {e}")
    
    def export_list_excel(
        self,
        fiscal_year: str,
        sub_scheme_code: str,
        district: Optional[str] = None,
        category: Optional[str] = None,
        class_type: Optional[str] = None
    ) -> StreamingResponse:
        """
        Export list data to Excel
        
        Returns:
            StreamingResponse with Excel file
        """
        try:
            items = self.repository.get_all_for_export(
                fiscal_year=fiscal_year,
                sub_scheme_code=sub_scheme_code,
                district=district,
                category=category,
                class_type=class_type
            )
            
            data_dict_list = []
            if items:
                columns = [c.name for c in items[0].__table__.columns]
                for item in items:
                    data_dict_list.append({col: getattr(item, col, None) for col in columns})
            
            df = pd.DataFrame(data_dict_list)
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Post Expenses List', index=False)
            
            output.seek(0)
            headers = {'Content-Disposition': 'attachment; filename="post_expenses_list.xlsx"'}
            return StreamingResponse(
                output,
                headers=headers,
                media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
        except Exception as e:
            logger.error(f"Failed to generate Post Expenses List Excel file: {e}", exc_info=True)
            raise ValueError(f"Could not generate Excel file: {e}")
    
    def export_original_workbook(
        self,
        db: Session,
        user_district: Optional[str] = None,
        sub_scheme_code: str = None,
        only_sheet: Optional[str] = None,
        fiscal_year: Optional[str] = None
    ) -> StreamingResponse:
        """
        Export original workbook template
        
        Args:
            db: Database session
            user_district: User's district filter
            sub_scheme_code: Sub-scheme code
            only_sheet: If specified, export only this sheet (e.g., "post_expenses")
            fiscal_year: Fiscal year filter
        
        Returns:
            StreamingResponse with Excel file
        """
        return export_original_workbook(
            db,
            user_district=user_district,
            sub_scheme_code=sub_scheme_code,
            only_sheet=only_sheet,
            fiscal_year=fiscal_year
        )

