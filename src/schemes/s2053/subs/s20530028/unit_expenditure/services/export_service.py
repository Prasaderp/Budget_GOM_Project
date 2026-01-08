"""Service for unit expenditure Excel export"""
from sqlalchemy.orm import Session
from typing import Optional
from fastapi.responses import StreamingResponse
from io import BytesIO
import pandas as pd
import logging

from ..repositories.unit_expenditure_repository import UnitExpenditureRepository
from .summary_service import UnitExpenditureSummaryService
from ..utils.formatters import get_ordered_keys, get_headers_map
from ...excel_export import export_original_workbook

logger = logging.getLogger(__name__)


class UnitExpenditureExportService:
    """Service for unit expenditure export operations"""
    
    def __init__(
        self,
        repository: UnitExpenditureRepository,
        summary_service: UnitExpenditureSummaryService
    ):
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
            data = self.summary_service.get_summary_and_charts(fiscal_year=fiscal_year)
            if not data:
                raise ValueError("Could not generate summary data")
            
            rows = data['summary_rows']
            totals = data['summary_totals']
            
            df = pd.DataFrame(rows + [totals])
            if 'UnitAccount_EN' in df.columns:
                df = df.drop(columns=['UnitAccount_EN'])
            
            headers_map = get_headers_map()
            ordered_keys = get_ordered_keys()
            
            cols = [k for k in ordered_keys if k in df.columns]
            df = df[cols]
            df.columns = [headers_map.get(c, c) for c in df.columns]
            
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Unit Expenditure Summary', index=False)
            output.seek(0)
            
            return StreamingResponse(
                output,
                headers={'Content-Disposition': 'attachment; filename="unit_expenditure_summary.xlsx"'},
                media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
        except Exception as e:
            logger.error(f"Failed to generate Unit Expenditure Summary Excel file: {e}", exc_info=True)
            raise ValueError(f"Could not generate Excel file: {e}")
    
    def export_list_excel(
        self,
        fiscal_year: str,
        sub_scheme_code: str,
        district: Optional[str] = None,
        primary_unit: Optional[str] = None
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
                primary_unit=primary_unit
            )
            
            data_list = []
            if items:
                columns = [c.name for c in items[0].__table__.columns]
                for item in items:
                    data_list.append({col: getattr(item, col, None) for col in columns})
            
            df = pd.DataFrame(data_list)
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Unit Expenditure List', index=False)
            output.seek(0)
            
            return StreamingResponse(
                output,
                headers={'Content-Disposition': 'attachment; filename="unit_expenditure_list.xlsx"'},
                media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
        except Exception as e:
            logger.error(f"Failed to generate Unit Expenditure List Excel file: {e}", exc_info=True)
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
            only_sheet: If specified, export only this sheet (e.g., "unit_expenditure")
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

