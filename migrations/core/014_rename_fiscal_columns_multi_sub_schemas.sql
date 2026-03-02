-- Migration: Rename fiscal year columns in all 4 sub-schema tables of scheme 2235
-- Applies relative naming: prev3/prev2/prev1/curr/curr/next instead of hardcoded years.

-- Table: district_expenditure_22350311
ALTER TABLE district_expenditure_22350311 RENAME COLUMN expenditure_2022_23 TO expenditure_prev3;
ALTER TABLE district_expenditure_22350311 RENAME COLUMN expenditure_2023_24 TO expenditure_prev2;
ALTER TABLE district_expenditure_22350311 RENAME COLUMN expenditure_2024_25 TO expenditure_prev1;
ALTER TABLE district_expenditure_22350311 RENAME COLUMN budget_grant_2025_26 TO budget_grant_curr;
ALTER TABLE district_expenditure_22350311 RENAME COLUMN revised_grant_2025_26 TO revised_grant_curr;
ALTER TABLE district_expenditure_22350311 RENAME COLUMN budget_estimate_2026_27 TO budget_estimate_next;

-- Table: district_expenditure_22350338
ALTER TABLE district_expenditure_22350338 RENAME COLUMN expenditure_2022_23 TO expenditure_prev3;
ALTER TABLE district_expenditure_22350338 RENAME COLUMN expenditure_2023_24 TO expenditure_prev2;
ALTER TABLE district_expenditure_22350338 RENAME COLUMN expenditure_2024_25 TO expenditure_prev1;
ALTER TABLE district_expenditure_22350338 RENAME COLUMN budget_grant_2025_26 TO budget_grant_curr;
ALTER TABLE district_expenditure_22350338 RENAME COLUMN revised_grant_2025_26 TO revised_grant_curr;
ALTER TABLE district_expenditure_22350338 RENAME COLUMN budget_estimate_2026_27 TO budget_estimate_next;

-- Table: district_expenditure_22353195
ALTER TABLE district_expenditure_22353195 RENAME COLUMN expenditure_2022_23 TO expenditure_prev3;
ALTER TABLE district_expenditure_22353195 RENAME COLUMN expenditure_2023_24 TO expenditure_prev2;
ALTER TABLE district_expenditure_22353195 RENAME COLUMN expenditure_2024_25 TO expenditure_prev1;
ALTER TABLE district_expenditure_22353195 RENAME COLUMN budget_grant_2025_26 TO budget_grant_curr;
ALTER TABLE district_expenditure_22353195 RENAME COLUMN revised_grant_2025_26 TO revised_grant_curr;
ALTER TABLE district_expenditure_22353195 RENAME COLUMN budget_estimate_2026_27 TO budget_estimate_next;

-- Table: district_expenditure_22353408
ALTER TABLE district_expenditure_22353408 RENAME COLUMN expenditure_2022_23 TO expenditure_prev3;
ALTER TABLE district_expenditure_22353408 RENAME COLUMN expenditure_2023_24 TO expenditure_prev2;
ALTER TABLE district_expenditure_22353408 RENAME COLUMN expenditure_2024_25 TO expenditure_prev1;
ALTER TABLE district_expenditure_22353408 RENAME COLUMN budget_grant_2025_26 TO budget_grant_curr;
ALTER TABLE district_expenditure_22353408 RENAME COLUMN revised_grant_2025_26 TO revised_grant_curr;
ALTER TABLE district_expenditure_22353408 RENAME COLUMN budget_estimate_2026_27 TO budget_estimate_next;
