"""Repository for UnitExpenditure database operations"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List, Tuple
from src.config import DCO_STAFF_IDENTIFIER
from src.utils_district import build_district_filter
from ...models import UnitExpenditure


class UnitExpenditureRepository:
    """Repository for UnitExpenditure database access"""
    
    def __init__(self, db: Session):
        """Initialize repository with database session"""
        self.db = db
    
    @property
    def session(self) -> Session:
        """Get database session"""
        return self.db
    
    def get_by_filters(
        self,
        fiscal_year: str,
        sub_scheme_code: str,
        auth_level: str,
        auth_unit: Optional[str],
        district: Optional[str] = None,
        primary_unit: Optional[str] = None,
        page: int = 1,
        page_size: int = 50
    ) -> Tuple[List[UnitExpenditure], int]:
        """
        Get unit expenditure records with filters and pagination
        
        Returns:
            tuple: (list of records, total count)
        """
        try:
            query = build_district_filter(
                self.db.query(UnitExpenditure),
                auth_level,
                auth_unit,
                UnitExpenditure
            ).filter(
                UnitExpenditure.fiscal_year == fiscal_year,
                UnitExpenditure.sub_scheme_code == sub_scheme_code
            )
            
            if district:
                query = query.filter(UnitExpenditure.district == district)
            if primary_unit:
                query = query.filter(UnitExpenditure.unit_account == primary_unit)
            
            total_count = query.with_entities(func.count(UnitExpenditure.id)).scalar() or 0
            items = query.order_by(UnitExpenditure.id).offset(
                (page - 1) * page_size
            ).limit(page_size).all()
            
            return items, total_count
        except Exception as e:
            raise ConnectionError(f"Database query failed: {str(e)}")
    
    def get_by_id(self, record_id: int, sub_scheme_code: str) -> Optional[UnitExpenditure]:
        """Get unit expenditure record by ID"""
        try:
            return self.db.query(UnitExpenditure).filter(
                UnitExpenditure.id == record_id,
                UnitExpenditure.sub_scheme_code == sub_scheme_code
            ).first()
        except Exception as e:
            raise ConnectionError(f"Database query failed: {str(e)}")
    
    def get_primary_units(
        self,
        fiscal_year: str,
        sub_scheme_code: str,
        district: Optional[str] = None
    ) -> List[str]:
        """Get distinct primary units (unit_account) matching filters"""
        try:
            query = self.db.query(UnitExpenditure.unit_account).distinct().filter(
                UnitExpenditure.fiscal_year == fiscal_year,
                UnitExpenditure.sub_scheme_code == sub_scheme_code
            )
            
            if district:
                query = query.filter(UnitExpenditure.district == district)
            
            results = query.order_by(UnitExpenditure.unit_account).limit(500).all()
            return [row[0] for row in results]
        except Exception as e:
            raise ConnectionError(f"Database query failed: {str(e)}")
    
    def get_record_data(
        self,
        fiscal_year: str,
        sub_scheme_code: str,
        district: str,
        primary_unit: str
    ) -> Optional[UnitExpenditure]:
        """Get record by natural key (district, unit_account)"""
        try:
            return self.db.query(UnitExpenditure).filter(
                UnitExpenditure.fiscal_year == fiscal_year,
                UnitExpenditure.sub_scheme_code == sub_scheme_code,
                UnitExpenditure.district == district,
                UnitExpenditure.unit_account == primary_unit
            ).first()
        except Exception as e:
            raise ConnectionError(f"Database query failed: {str(e)}")
    
    def get_summary_data(
        self,
        fiscal_year: str,
        district: Optional[str] = None,
        exclude_dco: bool = True
    ) -> List[Tuple]:
        """
        Get summary data aggregated by unit_account
        
        Returns:
            List of tuples: (unit_account, sum of each expenditure column)
        """
        try:
            base_filter = [UnitExpenditure.fiscal_year == fiscal_year]
            if district:
                base_filter.append(UnitExpenditure.district == district)
            elif exclude_dco:
                base_filter.append(UnitExpenditure.district != DCO_STAFF_IDENTIFIER)
            
            sum_exprs = [
                func.sum(UnitExpenditure.expenditure_2021_22).label("expenditure_2021_22"),
                func.sum(UnitExpenditure.expenditure_2022_23).label("expenditure_2022_23"),
                func.sum(UnitExpenditure.expenditure_2023_24).label("expenditure_2023_24"),
                func.sum(UnitExpenditure.budget_2024_25).label("budget_2024_25"),
                func.sum(UnitExpenditure.forecast_2024_25).label("forecast_2024_25"),
                func.sum(UnitExpenditure.budget_2025_26_estimating_officer).label("budget_2025_26_estimating_officer"),
                func.sum(UnitExpenditure.budget_2025_26_controlling_officer).label("budget_2025_26_controlling_officer"),
                func.sum(UnitExpenditure.budget_2025_26_admin_dept).label("budget_2025_26_admin_dept"),
                func.sum(UnitExpenditure.budget_2025_26_finance_dept).label("budget_2025_26_finance_dept")
            ]
            
            return self.db.query(
                UnitExpenditure.unit_account.label("unit_account"), *sum_exprs
            ).filter(*base_filter).group_by(UnitExpenditure.unit_account).order_by(
                UnitExpenditure.unit_account
            ).all()
        except Exception as e:
            raise ConnectionError(f"Database query failed: {str(e)}")
    
    def get_charts_data(
        self,
        fiscal_year: str,
        district: Optional[str] = None,
        exclude_dco: bool = True
    ) -> List[Tuple]:
        """
        Get charts data aggregated by district
        
        Returns:
            List of tuples with district and aggregated expenditure fields
        """
        try:
            base_filter = [UnitExpenditure.fiscal_year == fiscal_year]
            if district:
                base_filter.append(UnitExpenditure.district == district)
            elif exclude_dco:
                base_filter.append(UnitExpenditure.district != DCO_STAFF_IDENTIFIER)
            
            return self.db.query(
                UnitExpenditure.district,
                func.sum(UnitExpenditure.expenditure_2021_22).label("e21"),
                func.sum(UnitExpenditure.expenditure_2022_23).label("e22"),
                func.sum(UnitExpenditure.expenditure_2023_24).label("e23"),
                func.sum(UnitExpenditure.budget_2024_25).label("b24"),
                func.sum(UnitExpenditure.forecast_2024_25).label("f24"),
                func.sum(UnitExpenditure.budget_2025_26_estimating_officer).label("est"),
                func.sum(UnitExpenditure.budget_2025_26_controlling_officer).label("ctrl"),
                func.sum(UnitExpenditure.budget_2025_26_admin_dept).label("adm"),
                func.sum(UnitExpenditure.budget_2025_26_finance_dept).label("fin")
            ).filter(*base_filter).group_by(UnitExpenditure.district).order_by(
                UnitExpenditure.district
            ).all()
        except Exception as e:
            raise ConnectionError(f"Database query failed: {str(e)}")
    
    def get_all_for_export(
        self,
        fiscal_year: str,
        sub_scheme_code: str,
        district: Optional[str] = None,
        primary_unit: Optional[str] = None
    ) -> List[UnitExpenditure]:
        """Get all records for export (no pagination, batched)"""
        try:
            query = self.db.query(UnitExpenditure).filter(
                UnitExpenditure.fiscal_year == fiscal_year,
                UnitExpenditure.sub_scheme_code == sub_scheme_code
            )
            
            if district:
                query = query.filter(UnitExpenditure.district == district)
            if primary_unit:
                query = query.filter(UnitExpenditure.unit_account == primary_unit)
            
            return query.order_by(UnitExpenditure.id).all()
        except Exception as e:
            raise ConnectionError(f"Database query failed: {str(e)}")
    
    def update(self, record: UnitExpenditure) -> UnitExpenditure:
        """Update existing record"""
        try:
            self.db.commit()
            self.db.refresh(record)
            return record
        except Exception as e:
            self.db.rollback()
            raise ConnectionError(f"Database update failed: {str(e)}")
    
    def create(self, record: UnitExpenditure) -> UnitExpenditure:
        """Create new record"""
        try:
            self.db.add(record)
            self.db.commit()
            self.db.refresh(record)
            return record
        except Exception as e:
            self.db.rollback()
            raise ConnectionError(f"Database create failed: {str(e)}")

