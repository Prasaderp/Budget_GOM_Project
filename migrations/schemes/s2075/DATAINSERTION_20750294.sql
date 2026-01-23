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
    "expenditure_2022_23",
    "expenditure_2023_24",
    "expenditure_2024_25",
    "budget_estimate",
    "revised_estimate",
    "budget_estimate_2026_27",
    "remarks"
)
VALUES
  ('2025-26', '2075', '20750294', 'Thane', 0, 0, 0, 0, 0, 0, NULL),
  ('2025-26', '2075', '20750294', 'Palghar', 0, 0, 0, 0, 0, 0, NULL),
  ('2025-26', '2075', '20750294', 'Raigad', 0, 0, 0, 0, 0, 0, NULL),
  ('2025-26', '2075', '20750294', 'Sindhudurg', 0, 0, 0, 0, 0, 0, NULL)
ON CONFLICT (fiscal_year, sub_scheme_code, district) DO NOTHING;
