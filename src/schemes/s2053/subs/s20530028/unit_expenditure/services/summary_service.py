"""Service for unit expenditure summary and charts data calculation"""
from typing import Optional, Dict, Any, List
from src.utils_cache import memory_cache
from ..repositories.unit_expenditure_repository import UnitExpenditureRepository
from ..utils.formatters import get_internal_data_keys, get_ordered_keys, format_summary_row
import logging

logger = logging.getLogger(__name__)
_CACHE_TTL = 300


def _make_cache_key(prefix: str, *args) -> str:
    """Generate cache key"""
    return f"{prefix}|{'|'.join(str(a) for a in args)}"


class UnitExpenditureSummaryService:
    """Service for calculating unit expenditure summary and charts data"""
    
    def __init__(self, repository: UnitExpenditureRepository):
        """Initialize service with repository"""
        self.repository = repository
    
    def get_summary_and_charts(
        self,
        fiscal_year: str,
        district: Optional[str] = None,
        exclude_dco: bool = True
    ) -> Dict[str, Any]:
        """
        Get summary rows and charts data with caching
        
        Returns:
            Dict with summary_rows, summary_totals, internal_keys_ordered, charts
        """
        cache_key = _make_cache_key("unit_exp_combined", district or "all", fiscal_year)
        cached = memory_cache.get(cache_key)
        if cached:
            return cached
        
        try:
            # Get summary data
            summary_query = self.repository.get_summary_data(
                fiscal_year=fiscal_year,
                district=district,
                exclude_dco=exclude_dco
            )
            
            # Get charts data
            charts_query = self.repository.get_charts_data(
                fiscal_year=fiscal_year,
                district=district,
                exclude_dco=exclude_dco
            )
            
            # Process summary rows
            internal_keys = get_internal_data_keys()
            summary_rows = []
            totals = {k: 0 for k in internal_keys}
            
            for i, row in enumerate(summary_query, 1):
                formatted_row = format_summary_row(row, i, internal_keys)
                summary_rows.append(formatted_row)
                
                # Calculate totals
                for k in internal_keys:
                    v = int(getattr(row, k, 0) or 0)
                    totals[k] += v
            
            totals["SrNo"] = "--"
            totals["UnitAccount"] = "एकूण"
            
            # Process charts data
            labels, e21, e22, e23, b24, f24, est, ctrl, adm, fin = [], [], [], [], [], [], [], [], [], []
            for r in charts_query:
                labels.append(r.district or 'Unknown')
                e21.append(int(r.e21 or 0))
                e22.append(int(r.e22 or 0))
                e23.append(int(r.e23 or 0))
                b24.append(int(r.b24 or 0))
                f24.append(int(r.f24 or 0))
                est.append(int(r.est or 0))
                ctrl.append(int(r.ctrl or 0))
                adm.append(int(r.adm or 0))
                fin.append(int(r.fin or 0))
            
            result = {
                "summary_rows": summary_rows,
                "summary_totals": totals,
                "internal_keys_ordered": get_ordered_keys(),
                "charts": {
                    "area_trends": {
                        "labels": labels,
                        "exp_2021_22": e21,
                        "exp_2022_23": e22,
                        "exp_2023_24": e23
                    },
                    "doughnut_budget": {
                        "labels": labels,
                        "values": b24
                    },
                    "multi_axis_comparison": {
                        "labels": labels,
                        "budget_2024_25": b24,
                        "forecast_2024_25": f24
                    },
                    "radar_estimates": {
                        "labels": labels,
                        "estimating_officer": est,
                        "controlling_officer": ctrl,
                        "admin_dept": adm,
                        "finance_dept": fin
                    }
                }
            }
            
            memory_cache.set(cache_key, result, _CACHE_TTL)
            return result
            
        except Exception as e:
            logger.error(
                f"Error fetching/processing unit expenditure summary data (district={district}): {e}",
                exc_info=True
            )
            raise ConnectionError(f"Failed to generate summary data: {str(e)}")

