"""Subschema-specific prompt customizations for 0029 - Land Revenue Receipts"""
from dataclasses import dataclass
from typing import Optional, Dict

@dataclass
class PromptConfig:
    """Subschema-specific prompt configuration"""
    custom_context: Optional[Dict[str, str]] = None
    table_names: Optional[Dict[str, str]] = None

# Multi-table configuration
PROMPT_CONFIG = PromptConfig(
    custom_context={
        'data_relationships': """4 DIFFERENT TABLES with varying year ranges and structures:

Table 1: district_revenue_0029 (2017-2021, HAS district column)
  * Most recent data with district breakdown
  * 6 districts: Mumbai City, Mumbai Suburban, Thane, Raigad, Ratnagiri, Sindhudurg
  * Columns: district, actual_2017_18, actual_2018_19, actual_2019_20,
             budget_estimate_2020_21, revised_estimate_2020_21,
             budget_estimate_2021_22, table_section_code
  * Use for: Recent data (2017-2021), district-specific queries

Table 2: district_revenue_0029_section3 (2014-2018, NO district column!)
  * Mid-range historical data, aggregated across all districts
  * WARNING: NO "district" column exists!
  * Columns: actual_2014_15, actual_2015_16, actual_2016_17,
             budget_estimate_2017_18, revised_estimate_2017_18,
             budget_estimate_2018_19, table_section_code
  * Use for: Historical aggregated data (2014-2018)

Table 3: district_revenue_0029_section4 (2011-2015, NO district column!)
  * Oldest historical data, aggregated across all districts
  * WARNING: NO "district" column exists!
  * Columns: actual_2011_12, actual_2012_13, actual_2013_14,
             budget_estimate_2014_15, revised_estimate_2014_15,
             budget_estimate_2015_16, table_section_code
  * Use for: Oldest aggregated data (2011-2015)

Table 4: district_revenue_0029_jama_talmel (Reconciliation data, UNIQUE structure!)
  * Deposit and reconciliation data
  * CRITICAL: NO "district" column! Districts in COLUMN NAMES!
  * 12 columns (6 districts × 2): 
    mumbai_city_deposit, mumbai_city_reconciliation,
    mumbai_suburban_deposit, mumbai_suburban_reconciliation,
    thane_deposit, thane_reconciliation,
    raigad_deposit, raigad_reconciliation,
    ratnagiri_deposit, ratnagiri_reconciliation,
    sindhudurg_deposit, sindhudurg_reconciliation,
    table_section_code
  * Use for: Deposit/reconciliation queries""",
        
        'common_patterns': """- 6 Konkan districts ONLY: Mumbai City, Mumbai Suburban, Thane, Raigad, Ratnagiri, Sindhudurg
- NO Palghar, NO DCO Staff!
- Historical data: 2011-2021 (NOT current year)
- table_section_code: Categorizes different revenue types
- Fiscal year filtering: fiscal_year = '2025-26'
- Marathi terms:
  * जिल्हा/उपलेखाशिर्ष → district
  * प्रत्यक्ष जमा → actual receipt
  * अर्थसंकल्पीय जमा अंदाज → budget estimate
  * सुधारीत जमा अंदाज → revised estimate
  * जमा ताळमेळ → jama talmel (deposit & reconciliation)
  * ताळमेळ → reconciliation
  * जमा → receipt/deposit (context-dependent!)
- Table selection:
  * Keywords "deposit"/"reconciliation" → jama_talmel
  * Year 2017-2021 → district_revenue_0029
  * Year 2014-2018 → district_revenue_0029_section3
  * Year 2011-2015 → district_revenue_0029_section4""",
        
        'examples': """[Table 1 Example - WITH district]
Question: मुंबई शहर 2018-19 प्रत्यक्ष जमा
SQL: SELECT de."district", de."actual_2018_19"
FROM district_revenue_0029 de
WHERE de."fiscal_year" = '2025-26' AND de."district" = 'Mumbai City'
LIMIT {top_k};

[Table 3 Example - NO district!]
Question: 2015-16 चा प्रत्यक्ष जमा
SQL: SELECT de3."actual_2015_16"
FROM district_revenue_0029_section3 de3
WHERE de3."fiscal_year" = '2025-26'
LIMIT {top_k};

[Table 4 Example - NO district column!]  
Question: 2012-13 budget estimate
SQL: SELECT de4."budget_estimate_2014_15"
FROM district_revenue_0029_section4 de4
WHERE de4."fiscal_year" = '2025-26'
LIMIT {top_k};

[JamaTalmel Example - District in column name!]
Question: ठाणे जमा ताळमेळ
SQL: SELECT jt."thane_deposit", jt."thane_reconciliation"
FROM district_revenue_0029_jama_talmel jt
WHERE jt."fiscal_year" = '2025-26'
LIMIT {top_k};

[JamaTalmel Multi-district Example]
Question: सिंधुदुर्ग आणि रत्नागिरी deposit
SQL: SELECT jt."sindhudurg_deposit", jt."ratnagiri_deposit"
FROM district_revenue_0029_jama_talmel jt
WHERE jt."fiscal_year" = '2025-26'
LIMIT {top_k};"""
    },
    table_names={
        'district_revenue_table_1': 'district_revenue_0029',
        'district_revenue_table_3': 'district_revenue_0029_section3',
        'district_revenue_table_4': 'district_revenue_0029_section4',
        'jama_talmel_table': 'district_revenue_0029_jama_talmel'
    }
)
