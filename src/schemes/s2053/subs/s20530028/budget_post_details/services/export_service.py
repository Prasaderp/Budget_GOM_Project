"""Service for Excel export operations"""
from sqlalchemy.orm import Session
from typing import Optional
import pandas as pd
import io
from fastapi.responses import StreamingResponse
from ..repositories.budget_post_repository import BudgetPostRepository


class ExportService:
    """Service for exporting budget post details to Excel"""
    
    def __init__(self, repository: BudgetPostRepository):
        """Initialize service with repository"""
        self.repository = repository
    
    def export_to_excel(
        self,
        fiscal_year: str,
        sub_scheme_code: str,
        district: Optional[str] = None,
        category: Optional[str] = None,
        class_type: Optional[str] = None,
        designation_search: Optional[str] = None
    ) -> StreamingResponse:
        """
        Export budget post details to Excel
        
        Returns:
            StreamingResponse with Excel file
        """
        try:
            details = self.repository.get_all_for_export(
                fiscal_year=fiscal_year,
                sub_scheme_code=sub_scheme_code,
                district=district,
                category=category,
                class_type=class_type,
                designation_search=designation_search
            )
            
            # Convert to DataFrame
            columns = [c.name for c in details[0].__table__.columns if details] if details else []
            df = pd.DataFrame([
                {col: getattr(item, col, None) for col in columns}
                for item in details
            ])
            
            # Create Excel file in memory
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Budget Post Details', index=False)
            output.seek(0)
            
            return StreamingResponse(
                output,
                headers={'Content-Disposition': 'attachment; filename="budget_post_details.xlsx"'},
                media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
        except Exception as e:
            raise ConnectionError(f"Export failed: {str(e)}")

