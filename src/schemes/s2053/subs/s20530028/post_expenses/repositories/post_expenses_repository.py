"""Repository for PostExpenses database operations"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List, Tuple
from src.config import DCO_STAFF_IDENTIFIER
from src.utils_district import build_district_filter
from ...models import PostExpenses


class PostExpensesRepository:
    """Repository for PostExpenses database access"""
    
    def __init__(self, db: Session):
        """Initialize repository with database session"""
        self.db = db
    
    @property
    def session(self) -> Session:
        """Get database session"""
        return self.db
    
    def get_classes_by_filters(
        self,
        fiscal_year: str,
        sub_scheme_code: str,
        district: Optional[str] = None,
        category: Optional[str] = None
    ) -> List[str]:
        """Get distinct classes matching filters"""
        try:
            query = self.db.query(PostExpenses.class_type).distinct().filter(
                PostExpenses.fiscal_year == fiscal_year,
                PostExpenses.sub_scheme_code == sub_scheme_code
            )
            
            if district:
                query = query.filter(PostExpenses.district == district)
            if category:
                query = query.filter(PostExpenses.category == category)
            
            results = query.order_by(PostExpenses.class_type).all()
            return [row[0] for row in results]
        except Exception as e:
            raise ConnectionError(f"Database query failed: {str(e)}")
    
    def get_by_filters(
        self,
        fiscal_year: str,
        sub_scheme_code: str,
        auth_level: str,
        auth_unit: Optional[str],
        district: Optional[str] = None,
        category: Optional[str] = None,
        class_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 50
    ) -> Tuple[List[PostExpenses], int]:
        """
        Get post expenses with filters and pagination
        
        Returns:
            tuple: (list of records, total count)
        """
        try:
            query = build_district_filter(
                self.db.query(PostExpenses),
                auth_level,
                auth_unit,
                PostExpenses
            ).filter(
                PostExpenses.fiscal_year == fiscal_year,
                PostExpenses.sub_scheme_code == sub_scheme_code
            )
            
            if district:
                query = query.filter(PostExpenses.district == district)
            if category:
                query = query.filter(PostExpenses.category == category)
            if class_type:
                query = query.filter(PostExpenses.class_type == class_type)
            
            total_count = query.with_entities(func.count(PostExpenses.id)).scalar() or 0
            items = query.order_by(PostExpenses.id).offset(
                (page - 1) * page_size
            ).limit(page_size).all()
            
            return items, total_count
        except Exception as e:
            raise ConnectionError(f"Database query failed: {str(e)}")
    
    def get_by_id(self, record_id: int, sub_scheme_code: str) -> Optional[PostExpenses]:
        """Get post expense by ID"""
        try:
            return self.db.query(PostExpenses).filter(
                PostExpenses.id == record_id,
                PostExpenses.sub_scheme_code == sub_scheme_code
            ).first()
        except Exception as e:
            raise ConnectionError(f"Database query failed: {str(e)}")
    
    def get_record_data(
        self,
        fiscal_year: str,
        sub_scheme_code: str,
        district: str,
        category: str,
        class_type: str
    ) -> Optional[PostExpenses]:
        """Get record by natural key (district, category, class_type)"""
        try:
            return self.db.query(PostExpenses).filter(
                PostExpenses.fiscal_year == fiscal_year,
                PostExpenses.sub_scheme_code == sub_scheme_code,
                PostExpenses.district == district,
                PostExpenses.category == category,
                PostExpenses.class_type == class_type
            ).first()
        except Exception as e:
            raise ConnectionError(f"Database query failed: {str(e)}")
    
    def get_summary_post_counts(
        self,
        fiscal_year: str,
        district: Optional[str] = None
    ) -> List[Tuple]:
        """
        Get post counts aggregated by class_type and category for summary
        
        Returns:
            List of tuples: (class_type, category, TotalFilled, TotalVacant)
        """
        try:
            query = self.db.query(
                PostExpenses.class_type,
                PostExpenses.category,
                func.sum(PostExpenses.filled_posts).label("TotalFilled"),
                func.sum(PostExpenses.vacant_posts).label("TotalVacant")
            ).filter(PostExpenses.fiscal_year == fiscal_year)
            
            if district:
                query = query.filter(PostExpenses.district == district)
            else:
                query = query.filter(PostExpenses.district != DCO_STAFF_IDENTIFIER)
            
            return query.group_by(PostExpenses.class_type, PostExpenses.category).all()
        except Exception as e:
            raise ConnectionError(f"Database query failed: {str(e)}")
    
    def get_summary_expense_data(
        self,
        fiscal_year: str,
        district: Optional[str] = None
    ) -> List[Tuple]:
        """
        Get expense data aggregated by district for summary
        
        Returns:
            List of tuples with district and expense fields
        """
        try:
            query = self.db.query(
                PostExpenses.district,
                PostExpenses.medical_expenses,
                PostExpenses.festival_advance,
                PostExpenses.swagram_maharashtra_darshan,
                PostExpenses.seventh_pay_commission_difference_nps,
                PostExpenses.nps,
                PostExpenses.seventh_pay_commission_difference,
                PostExpenses.other
            ).filter(PostExpenses.fiscal_year == fiscal_year)
            
            if district:
                query = query.filter(PostExpenses.district == district)
            else:
                query = query.filter(PostExpenses.district != DCO_STAFF_IDENTIFIER)
            
            return query.all()
        except Exception as e:
            raise ConnectionError(f"Database query failed: {str(e)}")
    
    def get_charts_district_data(
        self,
        fiscal_year: str,
        district: Optional[str] = None
    ) -> List[Tuple]:
        """
        Get district-level aggregated data for charts
        
        Returns:
            List of tuples with district and aggregated expense fields
        """
        try:
            query = self.db.query(
                PostExpenses.district,
                func.sum(PostExpenses.filled_posts).label("total_filled"),
                func.sum(PostExpenses.vacant_posts).label("total_vacant"),
                func.sum(PostExpenses.medical_expenses).label("medical_exp"),
                func.sum(PostExpenses.festival_advance).label("festival_exp"),
                func.sum(PostExpenses.swagram_maharashtra_darshan).label("swagram_exp"),
                func.sum(PostExpenses.other).label("other_exp")
            ).filter(PostExpenses.fiscal_year == fiscal_year)
            
            if district:
                query = query.filter(PostExpenses.district == district)
            else:
                query = query.filter(PostExpenses.district != DCO_STAFF_IDENTIFIER)
            
            return query.group_by(PostExpenses.district).order_by(PostExpenses.district).all()
        except Exception as e:
            raise ConnectionError(f"Database query failed: {str(e)}")
    
    def get_charts_class_district_data(
        self,
        fiscal_year: str,
        district: Optional[str] = None
    ) -> List[Tuple]:
        """
        Get class and district aggregated data for charts
        
        Returns:
            List of tuples with district, class_type, filled, vacant
        """
        try:
            query = self.db.query(
                PostExpenses.district,
                PostExpenses.class_type,
                func.sum(PostExpenses.filled_posts).label("filled"),
                func.sum(PostExpenses.vacant_posts).label("vacant")
            ).filter(PostExpenses.fiscal_year == fiscal_year)
            
            if district:
                query = query.filter(PostExpenses.district == district)
            else:
                query = query.filter(PostExpenses.district != DCO_STAFF_IDENTIFIER)
            
            return query.group_by(
                PostExpenses.district, PostExpenses.class_type
            ).order_by(PostExpenses.district, PostExpenses.class_type).all()
        except Exception as e:
            raise ConnectionError(f"Database query failed: {str(e)}")
    
    def update(self, record: PostExpenses) -> PostExpenses:
        """Update existing record"""
        try:
            self.db.commit()
            self.db.refresh(record)
            return record
        except Exception as e:
            self.db.rollback()
            raise ConnectionError(f"Database update failed: {str(e)}")
    
    def bulk_update_by_district(
        self,
        district: str,
        fiscal_year: str,
        update_dict: dict
    ) -> int:
        """
        Bulk update records by district and fiscal year
        
        Returns:
            Number of rows updated
        """
        try:
            result = self.db.query(PostExpenses).filter(
                PostExpenses.district == district,
                PostExpenses.fiscal_year == fiscal_year
            ).update(update_dict, synchronize_session=False)
            self.db.commit()
            return result
        except Exception as e:
            self.db.rollback()
            raise ConnectionError(f"Database bulk update failed: {str(e)}")
    
    def get_all_for_export(
        self,
        fiscal_year: str,
        sub_scheme_code: str,
        district: Optional[str] = None,
        category: Optional[str] = None,
        class_type: Optional[str] = None
    ) -> List[PostExpenses]:
        """Get all records for export (no pagination)"""
        try:
            query = self.db.query(PostExpenses).filter(
                PostExpenses.fiscal_year == fiscal_year,
                PostExpenses.sub_scheme_code == sub_scheme_code
            )
            
            if district:
                query = query.filter(PostExpenses.district == district)
            if category:
                query = query.filter(PostExpenses.category == category)
            if class_type:
                query = query.filter(PostExpenses.class_type == class_type)
            
            return query.order_by(PostExpenses.id).all()
        except Exception as e:
            raise ConnectionError(f"Database query failed: {str(e)}")

