-- ==========================================
-- TABLE: district_expenditure_2075
-- Sub-scheme: 20750294 - District-wise Pension Expenditure
-- 4 districts: Thane, Palghar, Raigad, Sindhudurg
-- ==========================================

INSERT INTO district_expenditure_2075 (
    "fiscal_year",
    "scheme_code",
    "sub_scheme_code",
    "district",
    "expenditure_prev3",
    "expenditure_prev2",
    "expenditure_prev1",
    "budget_estimate_curr",
    "revised_estimate_curr",
    "budget_estimate_next",
    "remarks"
)
VALUES
  ('2025-26', '2075', '20750294', 'Thane', 0, 0, 0, 0, 0, 0, NULL),
  ('2025-26', '2075', '20750294', 'Palghar', 0, 0, 0, 0, 0, 0, NULL),
  ('2025-26', '2075', '20750294', 'Raigad', 0, 0, 0, 0, 0, 0, NULL),
  ('2025-26', '2075', '20750294', 'Sindhudurg', 0, 0, 0, 0, 0, 0, NULL)
ON CONFLICT (fiscal_year, sub_scheme_code, district, taluka) DO NOTHING;
