BEGIN;

-- ==========================================
-- TABLE: district_expenditure_76100158
-- Sub-scheme: 76100158 - District Expenditure
-- Total rows: 8 (one per Konkan district/office including DCO Staff)
-- This migration is safe to run on existing databases.
-- If rows already exist, ON CONFLICT DO NOTHING avoids duplicates.
-- ==========================================

INSERT INTO district_expenditure_76100158 (
    "fiscal_year",
    "scheme_code",
    "sub_scheme_code",
    "district",
    "expenditure_2022_23",
    "expenditure_2023_24",
    "expenditure_2024_25",
    "budget_estimate",
    "revised_estimate",
    "budget_estimate_2026_27",
    "remarks"
)
VALUES
  ('2025-26', '7610', '76100158', 'Mumbai City', 0, 0, 0, 0, 0, 0, NULL),
  ('2025-26', '7610', '76100158', 'Mumbai Suburban', 0, 0, 0, 0, 0, 0, NULL),
  ('2025-26', '7610', '76100158', 'Thane', 0, 0, 0, 0, 0, 0, NULL),
  ('2025-26', '7610', '76100158', 'Palghar', 0, 0, 0, 0, 0, 0, NULL),
  ('2025-26', '7610', '76100158', 'Raigad', 0, 0, 0, 0, 0, 0, NULL),
  ('2025-26', '7610', '76100158', 'Ratnagiri', 0, 0, 0, 0, 0, 0, NULL),
  ('2025-26', '7610', '76100158', 'Sindhudurg', 0, 0, 0, 0, 0, 0, NULL),
  ('2025-26', '7610', '76100158', 'DCO Staff', 0, 0, 0, 0, 0, 0, NULL)
ON CONFLICT DO NOTHING;

COMMIT;


