"""Schema context generator for 0029 - multi-table structure with intelligent routing"""
from typing import Dict, Optional
from src.core.base_config import BaseSchemeConfig

_CONTEXT_CACHE: Dict[str, Dict[str, str]] = {}

class SchemaContextGenerator:
    """Generates schema-specific context for 0029 with multi-table support"""
    
    @staticmethod
    def detect_table_from_query(question: str) -> str:
        """Detect which table to query based on keywords and year ranges"""
        question_lower = question.lower()
        
        # JamaTalmel detection (deposit/reconciliation keywords)
        if any(kw in question_lower for kw in ['deposit', 'reconciliation', 'जमा ताळमेळ', 'ताळमेळ']):
            return 'district_revenue_0029_jama_talmel'
        
        # Year-based routing
        if any(year in question for year in ['2017', '2018', '2019', '2020', '2021']):
            return 'district_revenue_0029'
        elif any(year in question for year in ['2014', '2015', '2016']):
            return 'district_revenue_0029_section3'
        elif any(year in question for year in ['2011', '2012', '2013']):
            return 'district_revenue_0029_section4'
        
        # Default to most recent table
        return 'district_revenue_0029'
    
    @staticmethod
    def get_table_structure_context(table_name: str) -> str:
        """Generate table-specific structure documentation"""
        if table_name == 'district_revenue_0029':
            return """- district_revenue_0029: Recent land revenue data (2017-2021)
  * HAS "district" column (6 Konkan districts)
  * Years: 2017-18, 2018-19, 2019-20, 2020-21, 2021-22
  * Columns: actual_2017_18, actual_2018_19, actual_2019_20,
             budget_estimate_2020_21, revised_estimate_2020_21,
             budget_estimate_2021_22, table_section_code
  * Districts: Mumbai City, Mumbai Suburban, Thane, Raigad, Ratnagiri, Sindhudurg
  * NO Palghar, NO DCO Staff"""
        
        elif table_name == 'district_revenue_0029_section3':
            return """- district_revenue_0029_section3: Mid-range historical data (2014-2018)
  * NO "district" column (aggregated data only!)
  * Years: 2014-15, 2015-16, 2016-17, 2017-18, 2018-19
  * Columns: actual_2014_15, actual_2015_16, actual_2016_17,
             budget_estimate_2017_18, revised_estimate_2017_18,
             budget_estimate_2018_19, table_section_code
  * Aggregated across all districts"""
        
        elif table_name == 'district_revenue_0029_section4':
            return """- district_revenue_0029_section4: Oldest historical data (2011-2015)
  * NO "district" column (aggregated data only!)
  * Years: 2011-12, 2012-13, 2013-14, 2014-15, 2015-16
  * Columns: actual_2011_12, actual_2012_13, actual_2013_14,
             budget_estimate_2014_15, revised_estimate_2014_15,
             budget_estimate_2015_16, table_section_code
  * Aggregated across all districts"""
        
        elif table_name == 'district_revenue_0029_jama_talmel':
            return """- district_revenue_0029_jama_talmel: Deposit & reconciliation data
  * UNIQUE STRUCTURE: NO "district" column! Districts in COLUMN names!
  * 6 districts × 2 columns (deposit + reconciliation) = 12 columns
  * Columns: mumbai_city_deposit, mumbai_city_reconciliation,
             mumbai_suburban_deposit, mumbai_suburban_reconciliation,
             thane_deposit, thane_reconciliation,
             raigad_deposit, raigad_reconciliation,
             ratnagiri_deposit, ratnagiri_reconciliation,
             sindhudurg_deposit, sindhudurg_reconciliation,
             table_section_code
  * Query pattern: SELECT thane_deposit, thane_reconciliation FROM ..."""
        
        return "Unknown table structure"
    
    @staticmethod
    def generate_context(config: BaseSchemeConfig, custom_context: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Generate complete context dictionary with module-level caching"""
        sub_scheme_code = config.code
        cache_key = f"s0029_{sub_scheme_code}"
        
        if cache_key in _CONTEXT_CACHE:
            return _CONTEXT_CACHE[cache_key]
        
        custom = custom_context or {}
        
        # Multi-table context
        context = {
            'table_name': 'district_revenue_0029',  # Default table
            'data_relationships': custom.get('data_relationships', """Multi-table structure with 4 different tables:

1. district_revenue_0029 (2017-2021, HAS district column)
2. district_revenue_0029_section3 (2014-2018, NO district!)
3. district_revenue_0029_section4 (2011-2015, NO district!)
4. district_revenue_0029_jama_talmel (Reconciliation, district in column names!)

Table selection based on year range and keywords."""),
            'common_patterns': custom.get('common_patterns', """- 6 Konkan districts ONLY: Mumbai City, Mumbai Suburban, Thane, Raigad, Ratnagiri, Sindhudurg
- NO Palghar, NO DCO Staff!
- Historical data: 2011-2021 (NOT current year)
- table_section_code: Categorizes revenue types
- Fiscal year filtering: fiscal_year = '2025-26'"""),
            'examples': custom.get('examples', """Example 1: Recent data with district
Question: मुंबई शहर 2018-19
SQL: SELECT district, actual_2018_19 FROM district_revenue_0029 
WHERE fiscal_year = '2025-26' AND district = 'Mumbai City';

Example 2: Historical aggregated data (NO district!)
Question: 2015-16 actual
SQL: SELECT actual_2015_16 FROM district_revenue_0029_section3
WHERE fiscal_year = '2025-26';

Example 3: JamaTalmel (district in column name!)
Question: ठाणे जमा ताळमेळ
SQL: SELECT thane_deposit, thane_reconciliation 
FROM district_revenue_0029_jama_talmel
WHERE fiscal_year = '2025-26';""")
        }
        
        _CONTEXT_CACHE[cache_key] = context
        return context
