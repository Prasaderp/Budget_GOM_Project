"""Shared category info service for s2045 subschemes"""
from typing import Dict, Any, List, Tuple, Type, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from collections import defaultdict
import logging

from src.config import DCO_STAFF_IDENTIFIER
from src.utils_cache import ttl_cache
from ..utils.constants import CLASS_MAPPING, CLASS_MR_MAP

logger = logging.getLogger(__name__)


class CategoryInfoService:
    """Service for category-wise information aggregation"""
    
    def __init__(self, post_expenses_model: Type):
        self.model = post_expenses_model
    
    @ttl_cache(ttl_seconds=300, max_size=20)
    def get_category_data(
        self,
        db: Session,
        sub_scheme_code: str,
        fiscal_year: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Get category-wise post information.
        
        CRITICAL: Filters by sub_scheme_code to ensure data isolation.
        
        Args:
            db: Database session
            sub_scheme_code: Subscheme code for data isolation (MANDATORY)
            fiscal_year: Optional fiscal year filter
        
        Returns:
            Tuple of (table_rows, totals_dict)
        """
        if not sub_scheme_code:
            raise ValueError("sub_scheme_code is required for data isolation")
        
        try:
            class_1_2_mr = CLASS_MR_MAP.get('Class-1 & 2', 'वर्ग-1 व 2')
            class_3_mr = CLASS_MR_MAP.get('Class-3', 'वर्ग-3')
            class_4_mr = CLASS_MR_MAP.get('Class-4', 'वर्ग-4')
            
            class_mapping = {
                '1': class_1_2_mr,
                '2': class_1_2_mr,
                '3': class_3_mr,
                '4': class_4_mr
            }
            class_order = [class_1_2_mr, class_3_mr, class_4_mr]
            
            query = db.query(
                self.model.class_type,
                self.model.category,
                func.sum(self.model.filled_posts).label("TotalFilled"),
                func.sum(self.model.vacant_posts).label("TotalVacant")
            ).filter(
                self.model.sub_scheme_code == sub_scheme_code
            )
            
            if fiscal_year:
                query = query.filter(self.model.fiscal_year == fiscal_year)
            
            query = query.filter(
                self.model.district != DCO_STAFF_IDENTIFIER
            ).group_by(
                self.model.class_type,
                self.model.category
            )
            
            aggregation_query = query.all()
            
            summary_data: Dict[str, Dict[str, int]] = {cls_name: {} for cls_name in class_order}
            totals: Dict[str, Any] = defaultdict(int)
            
            for result in aggregation_query:
                class_key = class_mapping.get(getattr(result, 'class_type', None))
                if not class_key:
                    continue
                
                filled = int(result.TotalFilled or 0)
                vacant = int(result.TotalVacant or 0)
                approved = filled + vacant
                
                category = getattr(result, 'category', None)
                if category == 'Permanent':
                    summary_data[class_key]['Filled_Perm'] = filled
                    summary_data[class_key]['Vacant_Perm'] = vacant
                    summary_data[class_key]['Approved_Perm'] = approved
                    totals['Filled_Perm'] += filled
                    totals['Vacant_Perm'] += vacant
                    totals['Approved_Perm'] += approved
                elif category == 'Temporary':
                    summary_data[class_key]['Filled_Temp'] = filled
                    summary_data[class_key]['Vacant_Temp'] = vacant
                    summary_data[class_key]['Approved_Temp'] = approved
                    totals['Filled_Temp'] += filled
                    totals['Vacant_Temp'] += vacant
                    totals['Approved_Temp'] += approved
            
            table_rows = []
            for i, class_name in enumerate(class_order, 1):
                row_data = summary_data.get(class_name, {})
                table_rows.append({
                    "Sr No.": i,
                    "Cadre": class_name,
                    "Approved - Permanent": row_data.get("Approved_Perm", 0),
                    "Approved - Temporary": row_data.get("Approved_Temp", 0),
                    "Filled - Permanent": row_data.get("Filled_Perm", 0),
                    "Filled - Temporary": row_data.get("Filled_Temp", 0),
                    "Vacant - Permanent": row_data.get("Vacant_Perm", 0),
                    "Vacant - Temporary": row_data.get("Vacant_Temp", 0)
                })
            
            totals['Sr No.'] = "--"
            totals['Cadre'] = "एकूण"
            totals_renamed = {
                "Sr No.": totals['Sr No.'],
                "Cadre": totals['Cadre'],
                "Approved - Permanent": totals['Approved_Perm'],
                "Approved - Temporary": totals['Approved_Temp'],
                "Filled - Permanent": totals['Filled_Perm'],
                "Filled - Temporary": totals['Filled_Temp'],
                "Vacant - Permanent": totals['Vacant_Perm'],
                "Vacant - Temporary": totals['Vacant_Temp']
            }
            
            return table_rows, totals_renamed
            
        except Exception as e:
            logger.error(
                f"Error in get_category_data: sub_scheme_code={sub_scheme_code}, "
                f"fiscal_year={fiscal_year}, error={type(e).__name__}: {str(e)}",
                exc_info=True
            )
            raise
