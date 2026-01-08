BEGIN;

-- ==========================================
-- TABLE: sub_head_expenditure_20750294
-- Sub-scheme: 20750294 - Sub-Head/Minor Head Expenditure
-- Fixed row structure (DCO only, no districts)
-- ==========================================

INSERT INTO sub_head_expenditure_20750294 (
    "fiscal_year",
    "scheme_code",
    "sub_scheme_code",
    "sub_head",
    "expenditure_2022_23",
    "expenditure_2023_24",
    "expenditure_2024_25",
    "budget_estimate",
    "revised_estimate",
    "budget_estimate_2026_27",
    "remarks"
)
VALUES
  ('2025-26', '2075', '20750294', 'मागणी क्र.सी-4-2075- संकिर्ण-सर्वसाधारण सेवा 101 (01) इनामदार व इतर अनुदानग्राही 04-निवृत्ती वेतने-(00) (01) आयुक्त कोकण (20750294)', 0, 0, 0, 0, 0, 0, NULL)
ON CONFLICT DO NOTHING;

COMMIT;

