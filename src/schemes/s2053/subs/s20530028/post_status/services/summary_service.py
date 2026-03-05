"""Service for Post Status summary data processing"""
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from collections import defaultdict
import logging

from src.config import DCO_STAFF_IDENTIFIER
from src.utils_cache import ttl_cache
from ..repositories.post_status_repository import PostStatusRepository
from ...config import (
    CLASS_1_2_KEY, CLASS_3_KEY, CLASS_4_KEY, VALID_CLASS_KEYS,
    CLASS_MAPPING, METRICS_DB_KEYS, METRICS_LABELS
)

logger = logging.getLogger(__name__)

CLASS_MR_MAP = {
    CLASS_1_2_KEY: 'वर्ग-1 व 2',
    CLASS_3_KEY: 'वर्ग-3',
    CLASS_4_KEY: 'वर्ग-4'
}


class PostStatusSummaryService:
    """Service for Post Status summary data aggregation and processing"""
    
    def __init__(self, db: Session):
        """Initialize service with database session"""
        self.repository = PostStatusRepository(db)
        self.db = db
    
    def _process_summary_data(
        self,
        summary: Dict,
        fiscal_year: str,
        district: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process summary data into metric rows and totals"""
        permanent_metric_rows = []
        temporary_metric_rows = []
        comparison_metrics_keys = []
        perm_category_totals = defaultdict(int)
        temp_category_totals = defaultdict(int)
        
        cost_fields = [
            'Salary', 'GradePay', 'SpecialPay', 'DearnessAllowance',
            'LocalSupplemetoryAllowance', 'HouseRentAllowance',
            'TravelAllowance', 'Other'
        ]
        
        for label in METRICS_LABELS:
            perm_row = {'Label': label}
            temp_row = {'Label': label}
            metric_key_for_comp = None
            
            for class_key in VALID_CLASS_KEYS + ['एकूण']:
                is_total_col = (class_key == 'एकूण')
                perm_filled_data = defaultdict(int)
                perm_vacant_data = defaultdict(int)
                temp_filled_data = defaultdict(int)
                temp_vacant_data = defaultdict(int)
                
                if not is_total_col:
                    perm_filled_data = summary['Permanent'].get(
                        CLASS_MR_MAP.get(class_key, class_key), {}
                    ).get('Filled', defaultdict(int))
                    perm_vacant_data = summary['Permanent'].get(
                        CLASS_MR_MAP.get(class_key, class_key), {}
                    ).get('Vacant', defaultdict(int))
                    temp_filled_data = summary['Temporary'].get(
                        CLASS_MR_MAP.get(class_key, class_key), {}
                    ).get('Filled', defaultdict(int))
                    temp_vacant_data = summary['Temporary'].get(
                        CLASS_MR_MAP.get(class_key, class_key), {}
                    ).get('Vacant', defaultdict(int))
                else:
                    for ck in VALID_CLASS_KEYS:
                        ck_mr = CLASS_MR_MAP.get(ck, ck)
                        perm_filled_class_data = summary['Permanent'].get(
                            ck_mr, {}
                        ).get('Filled', defaultdict(int))
                        perm_vacant_class_data = summary['Permanent'].get(
                            ck_mr, {}
                        ).get('Vacant', defaultdict(int))
                        temp_filled_class_data = summary['Temporary'].get(
                            ck_mr, {}
                        ).get('Filled', defaultdict(int))
                        temp_vacant_class_data = summary['Temporary'].get(
                            ck_mr, {}
                        ).get('Vacant', defaultdict(int))
                        
                        for dbk in METRICS_DB_KEYS:
                            perm_filled_data[dbk] += perm_filled_class_data.get(dbk, 0)
                            perm_vacant_data[dbk] += perm_vacant_class_data.get(dbk, 0)
                            temp_filled_data[dbk] += temp_filled_class_data.get(dbk, 0)
                            temp_vacant_data[dbk] += temp_vacant_class_data.get(dbk, 0)
                        
                        for field in [
                            'Posts', 'Salary', 'GradePay', 'SpecialPay',
                            'DearnessAllowance', 'LocalSupplemetoryAllowance',
                            'HouseRentAllowance', 'TravelAllowance', 'Other'
                        ]:
                            perm_filled_data[field] += perm_filled_class_data.get(field, 0)
                            perm_vacant_data[field] += perm_vacant_class_data.get(field, 0)
                            temp_filled_data[field] += temp_filled_class_data.get(field, 0)
                            temp_vacant_data[field] += temp_vacant_class_data.get(field, 0)
                
                val_perm_filled = val_perm_vacant = val_temp_filled = val_temp_vacant = 0
                
                if label == 'पदे':
                    metric_key_for_comp = 'पदे'
                    val_perm_filled = perm_filled_data.get('Posts', 0)
                    val_perm_vacant = perm_vacant_data.get('Posts', 0)
                    val_temp_filled = temp_filled_data.get('Posts', 0)
                    val_temp_vacant = temp_vacant_data.get('Posts', 0)
                elif label == 'वेतन':
                    metric_key_for_comp = 'वेतन'
                    val_perm_filled = perm_filled_data.get('Salary', 0)
                    val_temp_filled = temp_filled_data.get('Salary', 0)
                    val_perm_vacant = perm_vacant_data.get('Salary', 0)
                    val_temp_vacant = temp_vacant_data.get('Salary', 0)
                elif label == 'ग्रेड पे':
                    metric_key_for_comp = 'ग्रेड पे'
                    val_perm_filled = perm_filled_data.get('GradePay', 0)
                    val_temp_filled = temp_filled_data.get('GradePay', 0)
                    val_perm_vacant = perm_vacant_data.get('GradePay', 0)
                    val_temp_vacant = temp_vacant_data.get('GradePay', 0)
                elif label == 'विशेष वेतन':
                    metric_key_for_comp = 'विशेष वेतन'
                    val_perm_filled = perm_filled_data.get('SpecialPay', 0)
                    val_temp_filled = temp_filled_data.get('SpecialPay', 0)
                    val_perm_vacant = perm_vacant_data.get('SpecialPay', 0)
                    val_temp_vacant = temp_vacant_data.get('SpecialPay', 0)
                elif label == 'एकूण वेतन':
                    metric_key_for_comp = 'एकूण वेतन'
                    val_perm_filled = (
                        perm_filled_data.get('Salary', 0) +
                        perm_filled_data.get('GradePay', 0) +
                        perm_filled_data.get('SpecialPay', 0)
                    )
                    val_temp_filled = (
                        temp_filled_data.get('Salary', 0) +
                        temp_filled_data.get('GradePay', 0) +
                        temp_filled_data.get('SpecialPay', 0)
                    )
                    val_perm_vacant = (
                        perm_vacant_data.get('Salary', 0) +
                        perm_vacant_data.get('GradePay', 0) +
                        perm_vacant_data.get('SpecialPay', 0)
                    )
                    val_temp_vacant = (
                        temp_vacant_data.get('Salary', 0) +
                        temp_vacant_data.get('GradePay', 0) +
                        temp_vacant_data.get('SpecialPay', 0)
                    )
                elif label == 'महा.भत्ता':
                    metric_key_for_comp = 'महा.भत्ता'
                    val_perm_filled = perm_filled_data.get('DearnessAllowance', 0)
                    val_temp_filled = temp_filled_data.get('DearnessAllowance', 0)
                    val_perm_vacant = perm_vacant_data.get('DearnessAllowance', 0)
                    val_temp_vacant = temp_vacant_data.get('DearnessAllowance', 0)
                elif label == 'स्था.पु.भ.':
                    metric_key_for_comp = 'स्था.पु.भ.'
                    val_perm_filled = perm_filled_data.get('LocalSupplemetoryAllowance', 0)
                    val_temp_filled = temp_filled_data.get('LocalSupplemetoryAllowance', 0)
                    val_perm_vacant = perm_vacant_data.get('LocalSupplemetoryAllowance', 0)
                    val_temp_vacant = temp_vacant_data.get('LocalSupplemetoryAllowance', 0)
                elif label == 'घरभाडे':
                    metric_key_for_comp = 'घरभाडे'
                    val_perm_filled = perm_filled_data.get('HouseRentAllowance', 0)
                    val_temp_filled = temp_filled_data.get('HouseRentAllowance', 0)
                    val_perm_vacant = perm_vacant_data.get('HouseRentAllowance', 0)
                    val_temp_vacant = temp_vacant_data.get('HouseRentAllowance', 0)
                elif label == 'प्रवास भत्ता':
                    metric_key_for_comp = 'प्रवास भत्ता'
                    val_perm_filled = perm_filled_data.get('TravelAllowance', 0)
                    val_temp_filled = temp_filled_data.get('TravelAllowance', 0)
                    val_perm_vacant = perm_vacant_data.get('TravelAllowance', 0)
                    val_temp_vacant = temp_vacant_data.get('TravelAllowance', 0)
                elif label == 'इतर':
                    metric_key_for_comp = 'इतर'
                    val_perm_filled = perm_filled_data.get('Other', 0)
                    val_temp_filled = temp_filled_data.get('Other', 0)
                    val_perm_vacant = perm_vacant_data.get('Other', 0)
                    val_temp_vacant = temp_vacant_data.get('Other', 0)
                elif label == 'एकूण खर्च':
                    metric_key_for_comp = 'एकूण खर्च'
                    val_perm_filled = sum(perm_filled_data.get(k, 0) for k in cost_fields)
                    val_temp_filled = sum(temp_filled_data.get(k, 0) for k in cost_fields)
                    val_perm_vacant = sum(perm_vacant_data.get(k, 0) for k in cost_fields)
                    val_temp_vacant = sum(temp_vacant_data.get(k, 0) for k in cost_fields)
                
                perm_row[f'Filled_{class_key}'] = val_perm_filled
                perm_row[f'Vacant_{class_key}'] = val_perm_vacant
                temp_row[f'Filled_{class_key}'] = val_temp_filled
                temp_row[f'Vacant_{class_key}'] = val_temp_vacant
                
                if not is_total_col and metric_key_for_comp:
                    if metric_key_for_comp == 'पदे':
                        perm_category_totals[metric_key_for_comp] += val_perm_filled + val_perm_vacant
                        temp_category_totals[metric_key_for_comp] += val_temp_filled + val_temp_vacant
                    else:
                        perm_category_totals[metric_key_for_comp] += val_perm_filled
                        temp_category_totals[metric_key_for_comp] += val_temp_filled
            
            perm_row['Category_Total'] = perm_category_totals.get(metric_key_for_comp, 0)
            temp_row['Category_Total'] = temp_category_totals.get(metric_key_for_comp, 0)
            permanent_metric_rows.append(perm_row)
            temporary_metric_rows.append(temp_row)
            if metric_key_for_comp and metric_key_for_comp not in comparison_metrics_keys:
                comparison_metrics_keys.append(metric_key_for_comp)
        
        grand_totals_comparison = defaultdict(int)
        for key in comparison_metrics_keys:
            grand_totals_comparison[key] = (
                perm_category_totals.get(key, 0) + temp_category_totals.get(key, 0)
            )
        comparison_summary = [
            {'वर्ग': 'स्थायी', **perm_category_totals},
            {'वर्ग': 'अस्थायी', **temp_category_totals},
            {'वर्ग': 'एकूण', **grand_totals_comparison}
        ]
        
        final_class_summary = []
        grand_total_amt = 0
        grand_total_post = 0
        for cat in ['Permanent', 'Temporary']:
            cat_label = 'स्थायी' if cat == 'Permanent' else 'अस्थायी'
            cat_total_amt = 0
            cat_total_post = 0
            for cls_key in VALID_CLASS_KEYS:
                cls_mr = CLASS_MR_MAP.get(cls_key, cls_key)
                filled_data = summary.get(cat, {}).get(cls_mr, {}).get('Filled', defaultdict(int))
                vacant_data = summary.get(cat, {}).get(cls_mr, {}).get('Vacant', defaultdict(int))
                class_cat_total_amt = sum(filled_data.get(k, 0) for k in cost_fields)
                class_cat_total_post = filled_data.get('Posts', 0) + vacant_data.get('Posts', 0)
                final_class_summary.append({
                    "CategoryLabel": cat_label,
                    "ClassKey": cls_mr,
                    "Amt": class_cat_total_amt,
                    "Post": class_cat_total_post
                })
                cat_total_amt += class_cat_total_amt
                cat_total_post += class_cat_total_post
            final_class_summary.append({
                "CategoryLabel": cat_label,
                "ClassKey": "एकूण",
                "Amt": cat_total_amt,
                "Post": cat_total_post,
                "is_total": True
            })
            grand_total_amt += cat_total_amt
            grand_total_post += cat_total_post
        final_class_summary.append({
            "CategoryLabel": "स्थायी + अस्थायी",
            "ClassKey": "",
            "Amt": grand_total_amt,
            "Post": grand_total_post,
            "is_grand_total": True
        })
        
        return {
            'permanent_metric_rows': permanent_metric_rows,
            'temporary_metric_rows': temporary_metric_rows,
            'comparison_summary': comparison_summary,
            'comparison_metrics_keys': comparison_metrics_keys,
            'final_class_summary_table': final_class_summary,
            'grand_totals_comparison': dict(grand_totals_comparison)
        }
    
    @ttl_cache(ttl_seconds=180, use_global=True)
    def get_summary_data(
        self,
        fiscal_year: str = '2025-26',
        district: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get unified summary data for both district and overall post status
        
        Returns:
            dict with processed summary data or None on error
        """
        try:
            # Get summary by category, class, status
            query_results = self.repository.get_summary_by_category_class_status(
                fiscal_year, district
            )
            
            summary = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(int))))
            for row in query_results:
                category = row.category
                raw_class = row.class_type
                status = row.status
                class_key = CLASS_MAPPING.get(raw_class)
                if not category or not class_key or not status:
                    continue
                
                class_key_mr = CLASS_MR_MAP.get(class_key, class_key)
                target = summary[category][class_key_mr][status]
                for db_key in METRICS_DB_KEYS:
                    target[db_key] = int(getattr(row, db_key) or 0)
                target['Posts'] = target.get('posts', 0)
                target['Salary'] = target.get('salary', 0)
                target['GradePay'] = target.get('grade_pay', 0)
                target['SpecialPay'] = target.get('special_pay', 0)
                target['DearnessAllowance'] = target.get('dearness_allowance', 0)
                target['LocalSupplemetoryAllowance'] = target.get('local_supplementary_allowance', 0)
                target['HouseRentAllowance'] = target.get('house_rent_allowance', 0)
                target['TravelAllowance'] = target.get('travel_allowance', 0)
                target['Other'] = target.get('other', 0)
            
            processed = self._process_summary_data(summary, fiscal_year, district)
            
            # Get district summary by status
            district_rows = self.repository.get_summary_by_district_status(
                fiscal_year, district
            )
            
            district_summary = defaultdict(
                lambda: {"Filled": {"Posts": 0}, "Vacant": {"Posts": 0}, "TotalCost": 0}
            )
            district_components_sums = defaultdict(
                lambda: {"Salary": 0, "GradePay": 0, "SpecialPay": 0, "Allowances": 0}
            )
            
            for r in district_rows:
                d = getattr(r, 'district', None) or ''
                st = getattr(r, 'status', None) or ''
                posts_sum = int(getattr(r, 'posts', 0) or 0)
                if st in ('Filled', 'Vacant'):
                    district_summary[d][st]['Posts'] += posts_sum
                
                salary = int(getattr(r, 'salary', 0) or 0)
                grade = int(getattr(r, 'grade_pay', 0) or 0)
                special = int(getattr(r, 'special_pay', 0) or 0)
                da = int(getattr(r, 'dearness_allowance', 0) or 0)
                lsa = int(getattr(r, 'local_supplementary_allowance', 0) or 0)
                hra = int(getattr(r, 'house_rent_allowance', 0) or 0)
                travel = int(getattr(r, 'travel_allowance', 0) or 0)
                other = int(getattr(r, 'other', 0) or 0)
                allowances_total = da + lsa + hra + travel + other
                cost = salary + grade + special + allowances_total
                
                district_summary[d]['TotalCost'] += cost
                dc = district_components_sums[d]
                dc['Salary'] += salary
                dc['GradePay'] += grade
                dc['SpecialPay'] += special
                dc['Allowances'] += allowances_total
            
            # Get district category posts
            district_category_rows = self.repository.get_summary_by_district_category(
                fiscal_year, district
            )
            district_category_posts = defaultdict(lambda: {'Permanent': 0, 'Temporary': 0})
            
            for r in district_category_rows:
                d = getattr(r, 'district', None) or ''
                c = getattr(r, 'category', None) or ''
                p = int(getattr(r, 'posts', 0) or 0)
                if c in ('Permanent', 'Temporary'):
                    district_category_posts[d][c] += p
            
            return {
                **processed,
                'raw_summary_dict': summary,
                'class_keys_order': [CLASS_MR_MAP.get(k, k) for k in VALID_CLASS_KEYS],
                'district_summary': district_summary,
                'district_components_sums': district_components_sums,
                'district_category_posts': district_category_posts
            }
        
        except Exception as e:
            logger.error(
                f"Error fetching/processing post status summary data (district={district}): {e}",
                exc_info=True
            )
            return None
    
    def prepare_chart_data(
        self,
        summary_data: Dict[str, Any],
        labels: list[str]
    ) -> Dict[str, Any]:
        """
        Prepare chart data from summary data
        
        Args:
            summary_data: Summary data dict from get_summary_data
            labels: List of district labels for charts
            
        Returns:
            dict with chart data structures
        """
        try:
            district_summary = summary_data.get('district_summary', {})
            chart_data = {}
            
            dist_filled = []
            dist_vacant = []
            dist_cost = []
            dist_salary = []
            dist_grade = []
            dist_special = []
            dist_allowances = []
            
            for d in labels:
                ds = district_summary.get(d, {})
                dcomp = summary_data.get('district_components_sums', {}).get(d, {})
                dist_filled.append(int(ds.get('Filled', {}).get('Posts', 0) or 0))
                dist_vacant.append(int(ds.get('Vacant', {}).get('Posts', 0) or 0))
                dist_cost.append(int(ds.get('TotalCost', 0) or 0))
                dist_salary.append(int(dcomp.get('Salary', 0) or 0))
                dist_grade.append(int(dcomp.get('GradePay', 0) or 0))
                dist_special.append(int(dcomp.get('SpecialPay', 0) or 0))
                dist_allowances.append(int(dcomp.get('Allowances', 0) or 0))
            
            if not any(v > 0 for v in dist_filled + dist_vacant + dist_cost + dist_salary + dist_grade + dist_special + dist_allowances):
                dyn_labels = list(district_summary.keys())
                dist_filled = [
                    int((district_summary.get(d, {}).get('Filled', {}) or {}).get('Posts', 0) or 0)
                    for d in dyn_labels
                ]
                dist_vacant = [
                    int((district_summary.get(d, {}).get('Vacant', {}) or {}).get('Posts', 0) or 0)
                    for d in dyn_labels
                ]
                dist_cost = [
                    int((district_summary.get(d, {}) or {}).get('TotalCost', 0) or 0)
                    for d in dyn_labels
                ]
                dist_salary = [
                    int((summary_data.get('district_components_sums', {}).get(d, {}) or {}).get('Salary', 0) or 0)
                    for d in dyn_labels
                ]
                dist_grade = [
                    int((summary_data.get('district_components_sums', {}).get(d, {}) or {}).get('GradePay', 0) or 0)
                    for d in dyn_labels
                ]
                dist_special = [
                    int((summary_data.get('district_components_sums', {}).get(d, {}) or {}).get('SpecialPay', 0) or 0)
                    for d in dyn_labels
                ]
                dist_allowances = [
                    int((summary_data.get('district_components_sums', {}).get(d, {}) or {}).get('Allowances', 0) or 0)
                    for d in dyn_labels
                ]
                labels = dyn_labels
            
            dcmap = summary_data.get('district_category_posts', {})
            
            if labels:
                chart_data['district_posts_by_status'] = {
                    'labels': labels,
                    'भरलेली': dist_filled,
                    'रिक्त': dist_vacant,
                    'स्थायी': [
                        int((dcmap.get(d, {}) or {}).get('Permanent', 0) or 0)
                        for d in labels
                    ],
                    'अस्थायी': [
                        int((dcmap.get(d, {}) or {}).get('Temporary', 0) or 0)
                        for d in labels
                    ]
                }
                chart_data['district_total_cost'] = {
                    'labels': labels,
                    'values': dist_cost
                }
                chart_data['district_allowance_breakdown'] = {
                    'labels': labels,
                    'Salary': dist_salary,
                    'GradePay': dist_grade,
                    'SpecialPay': dist_special,
                    'Allowances': dist_allowances
                }
                chart_data['district_category_posts'] = {
                    'labels': labels,
                    'Permanent': [
                        int((dcmap.get(d, {}) or {}).get('Permanent', 0) or 0)
                        for d in labels
                    ],
                    'Temporary': [
                        int((dcmap.get(d, {}) or {}).get('Temporary', 0) or 0)
                        for d in labels
                    ]
                }
            
            return chart_data
        except Exception as e:
            logger.error(f"Error preparing chart data for Post Status: {e}", exc_info=True)
            return {}

