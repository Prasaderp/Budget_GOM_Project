"""Service for Post Status export operations"""
from sqlalchemy.orm import Session
from typing import Optional
import pandas as pd
import io
import logging

from fastapi.responses import StreamingResponse
from ...excel_export import export_original_workbook
from ..repositories.post_status_repository import PostStatusRepository
from .summary_service import PostStatusSummaryService
from ...models import PostStatus

logger = logging.getLogger(__name__)


class PostStatusExportService:
    """Service for Post Status export operations"""
    
    def __init__(self, db: Session):
        """Initialize service with database session"""
        self.repository = PostStatusRepository(db)
        self.summary_service = PostStatusSummaryService(db)
        self.db = db
    
    def export_summary_excel(
        self,
        fiscal_year: str
    ) -> StreamingResponse:
        """
        Export post status summary to Excel
        
        Returns:
            StreamingResponse with Excel file
        """
        try:
            summary_data = self.summary_service.get_summary_data(fiscal_year)
            if summary_data is None:
                raise ValueError("Could not generate summary data for download.")
            
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                CLASS_KEYS_ORDER = ['वर्ग-1 व 2', 'वर्ग-3', 'वर्ग-4', 'एकूण']
                METRICS_ORDER_COMP = summary_data.get('comparison_metrics_keys', [])
                
                perm_rows_df = pd.DataFrame(summary_data['permanent_metric_rows'])
                cols_perm = (
                    ['Label'] +
                    [f'{stat}_{cls}' for stat in ['Filled', 'Vacant'] for cls in CLASS_KEYS_ORDER] +
                    ['Category_Total']
                )
                perm_rows_df = perm_rows_df[cols_perm]
                perm_rows_df.to_excel(writer, sheet_name='Permanent Posts Summary', index=False)
                
                temp_rows_df = pd.DataFrame(summary_data['temporary_metric_rows'])
                cols_temp = (
                    ['Label'] +
                    [f'{stat}_{cls}' for stat in ['Filled', 'Vacant'] for cls in CLASS_KEYS_ORDER] +
                    ['Category_Total']
                )
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
            from fastapi import HTTPException
            raise HTTPException(status_code=500, detail=f"Could not generate Excel file: {e}")
    
    def export_list_excel(
        self,
        fiscal_year: str,
        sub_scheme_code: str,
        district: Optional[str] = None,
        category: Optional[str] = None,
        class_type: Optional[str] = None,
        status: Optional[str] = None
    ) -> StreamingResponse:
        """
        Export post status list to Excel
        
        Returns:
            StreamingResponse with Excel file
        """
        try:
            items = self.repository.get_all_for_export(
                fiscal_year, sub_scheme_code, district, category, class_type, status
            )
            
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
        except Exception as e:
            logger.error(f"Failed to generate Post Status List Excel file: {e}", exc_info=True)
            from fastapi import HTTPException
            raise HTTPException(status_code=500, detail=f"Could not generate Excel file: {e}")
    
    def export_original_workbook(
        self,
        sub_scheme_code: str,
        user_district: Optional[str] = None,
        fiscal_year: Optional[str] = None
    ) -> StreamingResponse:
        """
        Export original workbook template
        
        Returns:
            StreamingResponse with Excel file
        """
        return export_original_workbook(
            self.db,
            user_district=user_district,
            sub_scheme_code=sub_scheme_code,
            fiscal_year=fiscal_year
        )
    
    def export_sheet_only(
        self,
        sub_scheme_code: str,
        user_district: Optional[str] = None,
        fiscal_year: Optional[str] = None
    ) -> StreamingResponse:
        """
        Export only the post_status sheet from original workbook
        
        Returns:
            StreamingResponse with Excel file
        """
        return export_original_workbook(
            self.db,
            only_sheet="post_status",
            user_district=user_district,
            sub_scheme_code=sub_scheme_code,
            fiscal_year=fiscal_year
        )

