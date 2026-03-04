BEGIN;

-- ==========================================
-- TABLE: district_expenditure_76101871
-- Sub-scheme: 76101871 - District Expenditure
-- Total rows: 8 (one per Konkan district/office including DCO Staff)
-- This migration is safe to run on existing databases.
-- If rows already exist, ON CONFLICT DO NOTHING avoids duplicates.
-- ==========================================

INSERT INTO district_expenditure_76101871 (
    "fiscal_year",
    "scheme_code",
    "sub_scheme_code",
    "district",
    "expenditure_prev3",
    "expenditure_prev2",
    "expenditure_prev1",
    "budget_estimate",
    "revised_estimate",
    "budget_estimate_next",
    "remarks"
)
VALUES
  ('2025-26', '7610', '76101871', 'Mumbai City', 0, 0, 0, 0, 0, 0, NULL),
  ('2025-26', '7610', '76101871', 'Mumbai Suburban', 0, 0, 0, 0, 0, 0, NULL),
  ('2025-26', '7610', '76101871', 'Thane', 0, 0, 0, 0, 0, 0, NULL),
  ('2025-26', '7610', '76101871', 'Palghar', 0, 0, 0, 0, 0, 0, NULL),
  ('2025-26', '7610', '76101871', 'Raigad', 0, 0, 0, 0, 0, 0, NULL),
  ('2025-26', '7610', '76101871', 'Ratnagiri', 0, 0, 0, 0, 0, 0, NULL),
  ('2025-26', '7610', '76101871', 'Sindhudurg', 0, 0, 0, 0, 0, 0, NULL),
  ('2025-26', '7610', '76101871', 'DCO Staff', 0, 0, 0, 0, 0, 0, NULL)
ON CONFLICT DO NOTHING;

COMMIT;



