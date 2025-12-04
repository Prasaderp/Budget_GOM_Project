BEGIN;

-- ==========================================
-- TABLE: district_expenditure_64010018
-- Sub-scheme: 64010018 - Loans for Crop Husbandry
-- Total rows: 5 (one per Konkan district)
-- ==========================================

INSERT INTO district_expenditure_64010018 (
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
  ('2025-26', '6401', '64010018', 'Thane', 12500000, 15200000, 16800000, 18000000, 17500000, 19500000, 'Crop husbandry loans for agricultural development and crop production'),
  ('2025-26', '6401', '64010018', 'Palghar', 9800000, 11800000, 13200000, 14500000, 14000000, 15800000, 'Agricultural loans for crop production and farming support'),
  ('2025-26', '6401', '64010018', 'Raigad', 11200000, 13500000, 14800000, 16200000, 15700000, 17500000, 'Crop husbandry assistance for farmers and agricultural activities'),
  ('2025-26', '6401', '64010018', 'Ratnagiri', 8700000, 10500000, 11800000, 13000000, 12500000, 14200000, 'Agricultural development loans for crop production'),
  ('2025-26', '6401', '64010018', 'Sindhudurg', 7600000, 9200000, 10200000, 11200000, 10800000, 12200000, 'Crop husbandry loans for farming and agricultural support');

COMMIT;

-- Inserted 5 rows into district_expenditure_64010018

