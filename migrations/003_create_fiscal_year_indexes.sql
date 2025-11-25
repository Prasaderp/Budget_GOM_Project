-- Migration: Create indexes for fiscal_year columns
-- Version: 003_create_fiscal_year_indexes.sql
-- Description: Creates optimized indexes for fiscal_year queries

CREATE INDEX IF NOT EXISTS idx_budget_fiscal_year ON budget_post_details(fiscal_year);
CREATE INDEX IF NOT EXISTS idx_budget_fiscal_district ON budget_post_details(fiscal_year, district);
CREATE INDEX IF NOT EXISTS idx_budget_full_lookup ON budget_post_details(fiscal_year, district, category, class_type, designation);
CREATE INDEX IF NOT EXISTS idx_post_status_fiscal_year ON post_status(fiscal_year);
CREATE INDEX IF NOT EXISTS idx_post_status_full_lookup ON post_status(fiscal_year, district, category, class_type, status);
CREATE INDEX IF NOT EXISTS idx_post_expenses_fiscal_year ON post_expenses(fiscal_year);
CREATE INDEX IF NOT EXISTS idx_post_expenses_full_lookup ON post_expenses(fiscal_year, district, category, class_type);
CREATE INDEX IF NOT EXISTS idx_unit_expenditure_fiscal_year ON unit_expenditure(fiscal_year);
CREATE INDEX IF NOT EXISTS idx_unit_expenditure_full_lookup ON unit_expenditure(fiscal_year, district, unit_account);

