"""Service for post expenses charts data calculation"""
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from src.config import DCO_STAFF_IDENTIFIER
from src.utils_cache import ttl_cache
from ..repositories.post_expenses_repository import PostExpensesRepository
import logging

logger = logging.getLogger(__name__)


class PostExpensesChartsService:
    """Service for calculating post expenses charts data"""
    
    def __init__(self, repository: PostExpensesRepository):
        """Initialize service with repository"""
        self.repository = repository
    
    @ttl_cache(ttl_seconds=180, use_global=True)
    def get_charts_data(
        self,
        fiscal_year: str = '2025-26',
        district: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get unified charts data for both district and overall post expenses
        
        Returns:
            Dict with scatter_posts, pie_expenses, stacked_classes, polar_expenses
        """
        try:
            # Get district-level aggregated data
            district_data = self.repository.get_charts_district_data(
                fiscal_year=fiscal_year,
                district=district
            )
            
            # Get class and district aggregated data
            class_district_data = self.repository.get_charts_class_district_data(
                fiscal_year=fiscal_year,
                district=district
            )
            
            # Process district data
            districts = []
            filled_posts, vacant_posts = [], []
            medical_exp, festival_exp, swagram_exp, other_exp = [], [], [], []
            
            for row in district_data:
                districts.append(row.district or 'Unknown')
                filled_posts.append(int(row.total_filled or 0))
                vacant_posts.append(int(row.total_vacant or 0))
                medical_exp.append(int(row.medical_exp or 0))
                festival_exp.append(int(row.festival_exp or 0))
                swagram_exp.append(int(row.swagram_exp or 0))
                other_exp.append(int(row.other_exp or 0))
            
            # Process class data
            class_data = {}
            for row in class_district_data:
                district_name = row.district or 'Unknown'
                class_type = row.class_type or 'Unknown'
                if district_name not in class_data:
                    class_data[district_name] = {}
                class_data[district_name][class_type] = {
                    'filled': int(row.filled or 0),
                    'vacant': int(row.vacant or 0)
                }
            
            return {
                "scatter_posts": {
                    "districts": districts,
                    "filled": filled_posts,
                    "vacant": vacant_posts
                },
                "pie_expenses": {
                    "labels": ["Medical", "Festival", "Swagram", "Other"],
                    "values": [
                        sum(medical_exp),
                        sum(festival_exp),
                        sum(swagram_exp),
                        sum(other_exp)
                    ]
                },
                "stacked_classes": {
                    "districts": districts,
                    "class_data": class_data
                },
                "polar_expenses": {
                    "labels": districts,
                    "medical": medical_exp,
                    "other_combined": [
                        festival_exp[i] + swagram_exp[i] + other_exp[i] 
                        for i in range(len(districts))
                    ]
                }
            }
        
        except Exception as e:
            logger.error(f"Error generating post expenses charts data: {e}", exc_info=True)
            return {
                "scatter_posts": {"districts": [], "filled": [], "vacant": []},
                "pie_expenses": {"labels": [], "values": []},
                "stacked_classes": {"districts": [], "class_data": {}},
                "polar_expenses": {"labels": [], "medical": [], "other_combined": []}
            }

