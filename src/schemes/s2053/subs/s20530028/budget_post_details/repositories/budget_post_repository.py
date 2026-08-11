"""Repository for BudgetPostDetails database operations"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List
import logging
from src.utils_district import build_district_filter
from ...models import BudgetPostDetails

logger = logging.getLogger(__name__)


def escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class BudgetPostRepository:
    """Repository for BudgetPostDetails database access"""

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
        category: Optional[str] = None,
        class_type: Optional[str] = None,
        designation_search: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[List[BudgetPostDetails], int]:
        """
        Get budget post details with filters and pagination

        Returns:
            tuple: (list of records, total count)
        """
        try:
            query = build_district_filter(
                self.db.query(BudgetPostDetails),
                auth_level,
                auth_unit,
                BudgetPostDetails,
            ).filter(
                BudgetPostDetails.fiscal_year == fiscal_year,
                BudgetPostDetails.sub_scheme_code == sub_scheme_code,
            )

            if district:
                query = query.filter(BudgetPostDetails.district == district)
            if category:
                query = query.filter(BudgetPostDetails.category == category)
            if class_type:
                query = query.filter(BudgetPostDetails.class_type == class_type)
            if designation_search:
                safe_search = escape_like(designation_search)
                query = query.filter(
                    BudgetPostDetails.designation.ilike(f"%{safe_search}%", escape="\\")
                )

            total_count = (
                query.with_entities(func.count(BudgetPostDetails.id)).scalar() or 0
            )
            details = (
                query.order_by(BudgetPostDetails.id)
                .offset((page - 1) * page_size)
                .limit(page_size)
                .all()
            )

            return details, total_count
        except Exception:
            logger.error("budget_post_repo_query_err", exc_info=True)
            raise ConnectionError("Database query failed")

    def get_by_id(
        self, record_id: int, sub_scheme_code: str
    ) -> Optional[BudgetPostDetails]:
        """Get budget post detail by ID"""
        try:
            return (
                self.db.query(BudgetPostDetails)
                .filter(
                    BudgetPostDetails.id == record_id,
                    BudgetPostDetails.sub_scheme_code == sub_scheme_code,
                )
                .first()
            )
        except Exception as e:
            raise ConnectionError(f"Database query failed: {str(e)}")

    def get_designations(
        self,
        fiscal_year: str,
        sub_scheme_code: str,
        district: Optional[str] = None,
        category: Optional[str] = None,
        class_type: Optional[str] = None,
    ) -> List[str]:
        """Get distinct designations matching filters"""
        try:
            query = (
                self.db.query(BudgetPostDetails.designation)
                .distinct()
                .filter(
                    BudgetPostDetails.fiscal_year == fiscal_year,
                    BudgetPostDetails.sub_scheme_code == sub_scheme_code,
                )
            )

            if district:
                query = query.filter(BudgetPostDetails.district == district)
            if category:
                query = query.filter(BudgetPostDetails.category == category)
            if class_type:
                query = query.filter(BudgetPostDetails.class_type == class_type)

            results = query.order_by(BudgetPostDetails.designation).all()
            return [row[0] for row in results]
        except Exception as e:
            raise ConnectionError(f"Database query failed: {str(e)}")

    def get_record_data(
        self,
        fiscal_year: str,
        sub_scheme_code: str,
        district: str,
        category: str,
        class_type: str,
        designation: str,
    ) -> Optional[BudgetPostDetails]:
        """Get record by natural key"""
        try:
            return (
                self.db.query(BudgetPostDetails)
                .filter(
                    BudgetPostDetails.fiscal_year == fiscal_year,
                    BudgetPostDetails.sub_scheme_code == sub_scheme_code,
                    BudgetPostDetails.district == district,
                    BudgetPostDetails.category == category,
                    BudgetPostDetails.class_type == class_type,
                    BudgetPostDetails.designation == designation,
                )
                .first()
            )
        except Exception as e:
            raise ConnectionError(f"Database query failed: {str(e)}")

    def get_all_for_export(
        self,
        fiscal_year: str,
        sub_scheme_code: str,
        district: Optional[str] = None,
        category: Optional[str] = None,
        class_type: Optional[str] = None,
        designation_search: Optional[str] = None,
    ) -> List[BudgetPostDetails]:
        """Get all records for export (no pagination)"""
        try:
            query = self.db.query(BudgetPostDetails).filter(
                BudgetPostDetails.fiscal_year == fiscal_year,
                BudgetPostDetails.sub_scheme_code == sub_scheme_code,
            )

            if district:
                query = query.filter(BudgetPostDetails.district == district)
            if category:
                query = query.filter(BudgetPostDetails.category == category)
            if class_type:
                query = query.filter(BudgetPostDetails.class_type == class_type)
            if designation_search:
                query = query.filter(
                    BudgetPostDetails.designation.ilike(f"%{designation_search}%")
                )

            return query.order_by(BudgetPostDetails.id).all()
        except Exception as e:
            raise ConnectionError(f"Database query failed: {str(e)}")

    def update(self, record: BudgetPostDetails) -> BudgetPostDetails:
        """Flush pending changes. Commit is owned by the caller so it shares
        the transaction with consolidate_row()'s FOR UPDATE lock
        (docs/plan-taluka-remediation.md Phase 6)."""
        try:
            self.db.flush()
            return record
        except Exception as e:
            self.db.rollback()
            raise ConnectionError(f"Database update failed: {str(e)}")

    def create(self, record: BudgetPostDetails) -> BudgetPostDetails:
        """Create new record"""
        try:
            self.db.add(record)
            self.db.commit()
            self.db.refresh(record)
            return record
        except Exception as e:
            self.db.rollback()
            raise ConnectionError(f"Database create failed: {str(e)}")
