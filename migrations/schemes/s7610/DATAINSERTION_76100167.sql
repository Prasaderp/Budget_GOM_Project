BEGIN;

-- ==========================================
-- TABLE: district_expenditure_76100167
-- Sub-scheme: 76100167 - District Expenditure
-- Total rows: 8 (one per Konkan district/office including DCO Staff)
-- This migration is safe to run on existing databases.
-- If rows already exist, ON CONFLICT DO NOTHING avoids duplicates.
-- ==========================================

INSERT INTO district_expenditure_76100167 (
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
  ('2025-26', '7610', '76100167', 'Mumbai City', 0, 0, 0, 0, 0, 0, NULL),
  ('2025-26', '7610', '76100167', 'Mumbai Suburban', 0, 0, 0, 0, 0, 0, NULL),
  ('2025-26', '7610', '76100167', 'Thane', 0, 0, 0, 0, 0, 0, NULL),
  ('2025-26', '7610', '76100167', 'Palghar', 0, 0, 0, 0, 0, 0, NULL),
  ('2025-26', '7610', '76100167', 'Raigad', 0, 0, 0, 0, 0, 0, NULL),
  ('2025-26', '7610', '76100167', 'Ratnagiri', 0, 0, 0, 0, 0, 0, NULL),
  ('2025-26', '7610', '76100167', 'Sindhudurg', 0, 0, 0, 0, 0, 0, NULL),
  ('2025-26', '7610', '76100167', 'DCO Staff', 0, 0, 0, 0, 0, 0, NULL)
ON CONFLICT DO NOTHING;

COMMIT;



