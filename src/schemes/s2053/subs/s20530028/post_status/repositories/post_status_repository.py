"""Repository for PostStatus database operations"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List, Tuple, Any

from src.config import DCO_STAFF_IDENTIFIER
from src.utils_district import build_district_filter
from ...models import PostStatus


class PostStatusRepository:
    """Repository for PostStatus database access"""

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
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[PostStatus], int]:
        """
        Get post status records with filters and pagination

        Returns:
            tuple: (list of records, total count)
        """
        try:
            query = build_district_filter(
                self.db.query(PostStatus), auth_level, auth_unit, PostStatus
            ).filter(
                PostStatus.fiscal_year == fiscal_year,
                PostStatus.sub_scheme_code == sub_scheme_code,
            )

            if district:
                query = query.filter(PostStatus.district == district)
            if category:
                query = query.filter(PostStatus.category == category)
            if class_type:
                query = query.filter(PostStatus.class_type == class_type)
            if status:
                query = query.filter(PostStatus.status == status)

            total_count = query.with_entities(func.count(PostStatus.id)).scalar() or 0
            items = (
                query.order_by(PostStatus.id)
                .offset((page - 1) * page_size)
                .limit(page_size)
                .all()
            )

            return items, total_count
        except Exception as e:
            raise ConnectionError(f"Database query failed: {str(e)}")

    def get_by_id(self, record_id: int, sub_scheme_code: str) -> Optional[PostStatus]:
        """Get post status record by ID"""
        try:
            return (
                self.db.query(PostStatus)
                .filter(
                    PostStatus.id == record_id,
                    PostStatus.sub_scheme_code == sub_scheme_code,
                )
                .first()
            )
        except Exception as e:
            raise ConnectionError(f"Database query failed: {str(e)}")

    def get_by_natural_key(
        self,
        fiscal_year: str,
        sub_scheme_code: str,
        district: str,
        category: str,
        class_type: str,
        status: str,
    ) -> Optional[PostStatus]:
        """Get post status record by natural key (fiscal_year, district, category, class_type, status)"""
        try:
            return (
                self.db.query(PostStatus)
                .filter(
                    PostStatus.fiscal_year == fiscal_year,
                    PostStatus.sub_scheme_code == sub_scheme_code,
                    PostStatus.district == district,
                    PostStatus.category == category,
                    PostStatus.class_type == class_type,
                    PostStatus.status == status,
                )
                .first()
            )
        except Exception as e:
            raise ConnectionError(f"Database query failed: {str(e)}")

    def get_statuses(
        self,
        fiscal_year: str,
        sub_scheme_code: str,
        district: Optional[str] = None,
        category: Optional[str] = None,
        class_type: Optional[str] = None,
    ) -> List[str]:
        """Get distinct statuses matching filters"""
        try:
            query = (
                self.db.query(PostStatus.status)
                .distinct()
                .filter(
                    PostStatus.fiscal_year == fiscal_year,
                    PostStatus.sub_scheme_code == sub_scheme_code,
                )
            )

            if district:
                query = query.filter(PostStatus.district == district)
            if category:
                query = query.filter(PostStatus.category == category)
            if class_type:
                query = query.filter(PostStatus.class_type == class_type)

            results = query.order_by(PostStatus.status).all()
            return [row[0] for row in results]
        except Exception as e:
            raise ConnectionError(f"Database query failed: {str(e)}")

    def get_summary_by_category_class_status(
        self, fiscal_year: str, district: Optional[str] = None
    ) -> List[Any]:
        """
        Get summary data grouped by category, class_type, and status

        Returns list of query result rows with aggregated metrics
        """
        try:
            query = self.db.query(
                PostStatus.category,
                PostStatus.class_type,
                PostStatus.status,
                func.sum(PostStatus.posts).label("posts"),
                func.sum(PostStatus.salary).label("salary"),
                func.sum(PostStatus.grade_pay).label("grade_pay"),
                func.sum(PostStatus.dearness_allowance).label("dearness_allowance"),
                func.sum(PostStatus.special_pay).label("special_pay"),
                func.sum(PostStatus.local_supplementary_allowance).label(
                    "local_supplementary_allowance"
                ),
                func.sum(PostStatus.house_rent_allowance).label("house_rent_allowance"),
                func.sum(PostStatus.travel_allowance).label("travel_allowance"),
                func.sum(PostStatus.other).label("other"),
            ).filter(PostStatus.fiscal_year == fiscal_year)

            if district:
                query = query.filter(PostStatus.district == district)
            else:
                query = query.filter(PostStatus.district != DCO_STAFF_IDENTIFIER)

            return query.group_by(
                PostStatus.category, PostStatus.class_type, PostStatus.status
            ).all()
        except Exception as e:
            raise ConnectionError(f"Database query failed: {str(e)}")

    def get_summary_by_district_status(
        self, fiscal_year: str, district: Optional[str] = None
    ) -> List[Any]:
        """
        Get summary data grouped by district and status

        Returns list of query result rows with aggregated metrics
        """
        try:
            query = self.db.query(
                PostStatus.district,
                PostStatus.status,
                func.sum(PostStatus.posts).label("posts"),
                func.sum(PostStatus.salary).label("salary"),
                func.sum(PostStatus.grade_pay).label("grade_pay"),
                func.sum(PostStatus.special_pay).label("special_pay"),
                func.sum(PostStatus.dearness_allowance).label("dearness_allowance"),
                func.sum(PostStatus.local_supplementary_allowance).label(
                    "local_supplementary_allowance"
                ),
                func.sum(PostStatus.house_rent_allowance).label("house_rent_allowance"),
                func.sum(PostStatus.travel_allowance).label("travel_allowance"),
                func.sum(PostStatus.other).label("other"),
            ).filter(PostStatus.fiscal_year == fiscal_year)

            if district:
                query = query.filter(PostStatus.district == district)
            else:
                query = query.filter(PostStatus.district != DCO_STAFF_IDENTIFIER)

            return query.group_by(PostStatus.district, PostStatus.status).all()
        except Exception as e:
            raise ConnectionError(f"Database query failed: {str(e)}")

    def get_summary_by_district_category(
        self, fiscal_year: str, district: Optional[str] = None
    ) -> List[Any]:
        """
        Get summary data grouped by district and category (for posts count)

        Returns list of query result rows with aggregated posts
        """
        try:
            query = self.db.query(
                PostStatus.district,
                PostStatus.category,
                func.sum(PostStatus.posts).label("posts"),
            ).filter(PostStatus.fiscal_year == fiscal_year)

            if district:
                query = query.filter(PostStatus.district == district)
            else:
                query = query.filter(PostStatus.district != DCO_STAFF_IDENTIFIER)

            return query.group_by(PostStatus.district, PostStatus.category).all()
        except Exception as e:
            raise ConnectionError(f"Database query failed: {str(e)}")

    def update(self, record: PostStatus) -> PostStatus:
        """Flush pending changes. Commit is owned by the caller so it shares
        the transaction with consolidate_row()'s FOR UPDATE lock
        (docs/plan-taluka-remediation.md Phase 6)."""
        try:
            self.db.flush()
            return record
        except Exception as e:
            self.db.rollback()
            raise ConnectionError(f"Database update failed: {str(e)}")

    def create(self, record: PostStatus) -> PostStatus:
        """Create new post status record"""
        try:
            self.db.add(record)
            self.db.commit()
            self.db.refresh(record)
            return record
        except Exception as e:
            self.db.rollback()
            raise ConnectionError(f"Database create failed: {str(e)}")

    def get_all_for_export(
        self,
        fiscal_year: str,
        sub_scheme_code: str,
        district: Optional[str] = None,
        category: Optional[str] = None,
        class_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[PostStatus]:
        """Get all records matching filters for export (no pagination)"""
        try:
            query = self.db.query(PostStatus).filter(
                PostStatus.fiscal_year == fiscal_year,
                PostStatus.sub_scheme_code == sub_scheme_code,
            )

            if district:
                query = query.filter(PostStatus.district == district)
            if category:
                query = query.filter(PostStatus.category == category)
            if class_type:
                query = query.filter(PostStatus.class_type == class_type)
            if status:
                query = query.filter(PostStatus.status == status)

            return query.order_by(PostStatus.id).all()
        except Exception as e:
            raise ConnectionError(f"Database query failed: {str(e)}")
