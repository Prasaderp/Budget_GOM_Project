"""
Shared Abstract Data Service for all s2053 sub-schemes.

This service consolidates duplicate logic across all sub-schemes (20530019, 20530028,
20530153, 20530162, 20530233, 20530242, 20530304, 20530313, 20530378, 20530387).

Key improvements:
1. DRY principle - single source of truth for abstract data logic
2. Pandas deprecation fix - aggfunc='sum' instead of aggfunc=sum
3. Fiscal year awareness - includes fiscal_year in cache keys
4. Performance optimization - consolidates 4 queries into optimized calls
5. Defensive programming - null checks, type validation, error handling
"""
from typing import Dict, Any, List, Optional, Type
from sqlalchemy.orm import Session
from sqlalchemy import func
import pandas as pd
import logging

from src.config import REGULAR_DISTRICTS, DCO_STAFF_IDENTIFIER, DISTRICTS_MR
from src.utils_cache import ttl_cache

logger = logging.getLogger(__name__)


class SubSchemeAbstractService:
    """
    Generic abstract data service for s2053 sub-schemes.
    
    This service handles district-wise abstract reporting with optimized queries,
    proper caching, and pandas 3.0 compatibility.
    
    Usage:
        from .models import UnitExpenditure
        from .config import UNIT_ACCOUNT_MAP_MR
        
        service = SubSchemeAbstractService(
            model_class=UnitExpenditure,
            unit_account_map=UNIT_ACCOUNT_MAP_MR,
            fiscal_year_field='budget_2025_26_estimating_officer'
        )
        
        data = service.get_district_abstract_data(db, 'Thane', '2025-26')
    """
    
    def __init__(
        self,
        model_class: Type,
        unit_account_map: Dict[str, str],
        fiscal_year_field: str = 'budget_2025_26_estimating_officer',
        expenditure_field: str = 'expenditure_2023_24',
        current_budget_field: str = 'budget_2024_25',
        forecast_field: str = 'forecast_2024_25'
    ):
        """
        Initialize abstract service with model-specific configuration.
        
        Args:
            model_class: SQLAlchemy model class (e.g., UnitExpenditure)
            unit_account_map: Marathi translation map for unit accounts
            fiscal_year_field: Column name for target fiscal year budget
            expenditure_field: Column name for previous expenditure
            current_budget_field: Column name for current year budget
            forecast_field: Column name for current year forecast
        """
        self.model = model_class
        self.unit_map = unit_account_map
        self.fy_field = fiscal_year_field
        self.expenditure_field = expenditure_field
        self.current_budget_field = current_budget_field
        self.forecast_field = forecast_field
    
    @ttl_cache(ttl_seconds=180, use_global=True, include_fiscal_year=True)
    def get_district_abstract_data(
        self,
        db: Session,
        district: str,
        fiscal_year: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Get district-wise abstract table data.
        
        Args:
            db: Database session
            district: District name
            fiscal_year: Fiscal year for cache isolation (e.g., '2025-26')
        
        Returns:
            DataFrame with unit accounts as index and district data
        
        Raises:
            ValueError: If district is None or empty
        """
        if not district:
            raise ValueError("district parameter cannot be empty")
        
        try:
            # Query data for specific district
            data_query = db.query(
                self.model.unit_account,
                self.model.district,
                getattr(self.model, self.fy_field)
            ).filter(self.model.district == district).all()
            
            # Handle empty result
            if not data_query:
                logger.info(f"No data found for district: {district}, fiscal_year: {fiscal_year}")
                return pd.DataFrame(
                    columns=['Subheadings', district]
                ).set_index('Subheadings')
            
            # Convert to DataFrame
            df = pd.DataFrame(data_query, columns=['Subheadings', 'District', 'Value'])
            
            # Create pivot table with FIXED aggfunc (string instead of function)
            # This fixes the FutureWarning and ensures pandas 3.0 compatibility
            pivot_df = df.pivot_table(
                index='Subheadings',
                columns='District',
                values='Value',
                fill_value=0,
                aggfunc='sum'  # ✅ String - pandas 3.0 compatible
            )
            
            # Ensure column ordering
            pivot_df = pivot_df.reindex(columns=[district], fill_value=0)
            
            # Convert to integers (defensive - handle potential NaN/None)
            numeric_cols = pivot_df.columns
            for col in numeric_cols:
                pivot_df[col] = pd.to_numeric(
                    pivot_df[col],
                    errors='coerce'
                ).fillna(0).astype(int)
            
            return pivot_df
            
        except Exception as e:
            logger.error(
                f"Error in get_district_abstract_data: district={district}, "
                f"fiscal_year={fiscal_year}, error={type(e).__name__}: {str(e)}",
                exc_info=True
            )
            raise
    
    @ttl_cache(ttl_seconds=180, use_global=True, include_fiscal_year=True)
    def get_district_abstract_charts_data(
        self,
        db: Session,
        district: str,
        fiscal_year: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get aggregated chart data for a specific district.
        
        Args:
            db: Database session
            district: District name
            fiscal_year: Fiscal year for cache isolation
        
        Returns:
            Dict with labels and data arrays for charting
        """
        if not district:
            raise ValueError("district parameter cannot be empty")
        
        try:
            # Aggregated query with all metrics
            data_query = db.query(
                self.model.unit_account,
                func.sum(getattr(self.model, self.fy_field)).label('budget'),
                func.sum(getattr(self.model, self.expenditure_field)).label('expenditure'),
                func.sum(getattr(self.model, self.current_budget_field)).label('current_budget'),
                func.sum(getattr(self.model, self.forecast_field)).label('forecast')
            ).filter(
                self.model.district == district
            ).group_by(self.model.unit_account).all()
            
            # Build parallel arrays for charting
            unit_accounts = []
            budgets, expenditures, current_budgets, forecasts = [], [], [], []
            
            for row in data_query:
                # Translate to Marathi with fallback
                unit_accounts.append(
                    self.unit_map.get(row.unit_account, row.unit_account)
                )
                # Defensive null handling
                budgets.append(int(row.budget or 0))
                expenditures.append(int(row.expenditure or 0))
                current_budgets.append(int(row.current_budget or 0))
                forecasts.append(int(row.forecast or 0))
            
            return {
                'labels': unit_accounts,
                'budgets': budgets,
                'expenditures': expenditures,
                'current_budgets': current_budgets,
                'forecasts': forecasts
            }
            
        except Exception as e:
            logger.error(
                f"Error in get_district_abstract_charts_data: district={district}, "
                f"fiscal_year={fiscal_year}, error={type(e).__name__}: {str(e)}",
                exc_info=True
            )
            raise
    
    @ttl_cache(ttl_seconds=180, use_global=True, include_fiscal_year=True)
    def get_all_districts_abstract_charts_data(
        self,
        db: Session,
        fiscal_year: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get aggregated chart data for all districts.
        
        Args:
            db: Database session
            fiscal_year: Fiscal year for cache isolation
        
        Returns:
            Dict with labels and data arrays for charting
        """
        try:
            # Aggregated query across all districts (excluding DCO Staff)
            data_query = db.query(
                self.model.district,
                func.sum(getattr(self.model, self.fy_field)).label('budget'),
                func.sum(getattr(self.model, self.expenditure_field)).label('expenditure'),
                func.sum(getattr(self.model, self.current_budget_field)).label('current_budget'),
                func.sum(getattr(self.model, self.forecast_field)).label('forecast')
            ).filter(
                self.model.district != DCO_STAFF_IDENTIFIER
            ).group_by(self.model.district).order_by(self.model.district).all()
            
            # Build parallel arrays
            districts = []
            budgets, expenditures, current_budgets, forecasts = [], [], [], []
            
            for row in data_query:
                # Translate district to Marathi
                districts.append(DISTRICTS_MR.get(row.district, row.district))
                budgets.append(int(row.budget or 0))
                expenditures.append(int(row.expenditure or 0))
                current_budgets.append(int(row.current_budget or 0))
                forecasts.append(int(row.forecast or 0))
            
            return {
                'labels': districts,
                'budgets': budgets,
                'expenditures': expenditures,
                'current_budgets': current_budgets,
                'forecasts': forecasts
            }
            
        except Exception as e:
            logger.error(
                f"Error in get_all_districts_abstract_charts_data: "
                f"fiscal_year={fiscal_year}, error={type(e).__name__}: {str(e)}",
                exc_info=True
            )
            raise
    
    @ttl_cache(ttl_seconds=180, use_global=True, include_fiscal_year=True)
    def get_abstract_data(
        self,
        db: Session,
        fiscal_year: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Get complete abstract data for all districts.
        
        Args:
            db: Database session
            fiscal_year: Fiscal year for cache isolation
        
        Returns:
            DataFrame with unit accounts as rows, districts as columns, plus Total
        """
        try:
            # Query all districts (excluding DCO Staff)
            data_query = db.query(
                self.model.unit_account,
                self.model.district,
                getattr(self.model, self.fy_field)
            ).filter(
                self.model.district != DCO_STAFF_IDENTIFIER
            ).all()
            
            # Handle empty result
            if not data_query:
                logger.info(f"No data found for all districts, fiscal_year: {fiscal_year}")
                return pd.DataFrame(
                    columns=['Subheadings'] + REGULAR_DISTRICTS + ['Total']
                ).set_index('Subheadings')
            
            # Convert to DataFrame
            df = pd.DataFrame(data_query, columns=['Subheadings', 'District', 'Value'])
            
            # Create pivot table (PANDAS 3.0 COMPATIBLE)
            pivot_df = df.pivot_table(
                index='Subheadings',
                columns='District',
                values='Value',
                fill_value=0,
                aggfunc='sum'  # ✅ String - pandas 3.0 compatible
            )
            
            # Ensure all districts are present in correct order
            pivot_df = pivot_df.reindex(columns=REGULAR_DISTRICTS, fill_value=0)
            
            # Convert to integers (defensive null handling)
            numeric_cols = pivot_df.columns
            for col in numeric_cols:
                pivot_df[col] = pd.to_numeric(
                    pivot_df[col],
                    errors='coerce'
                ).fillna(0).astype(int)
            
            # Add Total column (sum across all districts)
            pivot_df['Total'] = pivot_df.sum(axis=1)
            
            return pivot_df
            
        except Exception as e:
            logger.error(
                f"Error in get_abstract_data: "
                f"fiscal_year={fiscal_year}, error={type(e).__name__}: {str(e)}",
                exc_info=True
            )
            raise
