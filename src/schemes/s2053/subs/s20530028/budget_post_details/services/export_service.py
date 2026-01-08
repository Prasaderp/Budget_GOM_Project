"""Service for Excel export operations - Budget Post Details.

This module handles Excel export for budget post details using the
centralized response utility for cache-safe downloads.
"""
from typing import Optional
import pandas as pd
import io

from starlette.responses import StreamingResponse
from ...shared.utils.response_utils import create_excel_response
from ..repositories.budget_post_repository import BudgetPostRepository


class ExportService:
    """Service for exporting budget post details to Excel."""
    
    def __init__(self, repository: BudgetPostRepository):
        """Initialize service with repository."""
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
        Export budget post details to Excel with cache-safe response.
        
        Args:
            fiscal_year: The fiscal year to export data for.
            sub_scheme_code: Sub-scheme code for filtering.
            district: Optional district filter.
            category: Optional category filter.
            class_type: Optional class type filter.
            designation_search: Optional designation search text.
        
        Returns:
            StreamingResponse with cache-prevention headers.
        
        Raises:
            ConnectionError: If export operation fails.
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
            
            # Convert to DataFrame efficiently
            if details:
                columns = [c.name for c in details[0].__table__.columns]
                data = [{col: getattr(item, col, None) for col in columns} for item in details]
            else:
                data = []
            
            df = pd.DataFrame(data)
            
            # Create Excel file in memory
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Budget Post Details', index=False)
            
            return create_excel_response(
                content=output,
                base_filename="budget_post_details",
                fiscal_year=fiscal_year
            )
        except Exception as e:
            raise ConnectionError(f"Export failed: {str(e)}")


