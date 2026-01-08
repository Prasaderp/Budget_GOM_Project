BEGIN;

-- ==========================================
-- TABLE: district_expenditure_62450017
-- Sub-scheme: 62450017 - Loans for Natural Calamities (Other Loans)
-- Total rows: 5 (one per Konkan district)
-- ==========================================

INSERT INTO district_expenditure_62450017 (
    "fiscal_year",
    "scheme_code",
    "sub_scheme_code",
    "district",
    "expenditure_2022_23",
    "expenditure_2023_24",
    "expenditure_2024_25",
    "budget_grant_2025_26",
    "revised_estimate_2025_26",
    "budget_estimate_2026_27",
    "remarks"
)
VALUES
  ('2025-26', '6245', '62450017', 'Thane', 12500000, 15200000, 16800000, 18000000, 17500000, 19500000, 'Natural calamity relief loans for flood and cyclone affected areas'),
  ('2025-26', '6245', '62450017', 'Palghar', 9800000, 11800000, 13200000, 14500000, 14000000, 15800000, 'Disaster relief loans for coastal areas and agricultural damage'),
  ('2025-26', '6245', '62450017', 'Raigad', 11200000, 13500000, 14800000, 16200000, 15700000, 17500000, 'Cyclone and flood relief assistance for affected families'),
  ('2025-26', '6245', '62450017', 'Ratnagiri', 8700000, 10500000, 11800000, 13000000, 12500000, 14200000, 'Natural disaster loans for coastal region rehabilitation'),
  ('2025-26', '6245', '62450017', 'Sindhudurg', 7600000, 9200000, 10200000, 11200000, 10800000, 12200000, 'Relief loans for flood and landslide affected areas');

COMMIT;

-- Inserted 5 rows into district_expenditure_62450017

