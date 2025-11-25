-- Migration: Add fiscal_year columns to budget tables
-- Version: 002_add_fiscal_year_columns.sql
-- Description: Adds fiscal_year column to budget_post_details, post_status, post_expenses, unit_expenditure

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'budget_post_details' AND column_name = 'fiscal_year'
    ) THEN
        ALTER TABLE budget_post_details ADD COLUMN fiscal_year VARCHAR DEFAULT '2025-26';
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'post_status' AND column_name = 'fiscal_year'
    ) THEN
        ALTER TABLE post_status ADD COLUMN fiscal_year VARCHAR DEFAULT '2025-26';
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'post_expenses' AND column_name = 'fiscal_year'
    ) THEN
        ALTER TABLE post_expenses ADD COLUMN fiscal_year VARCHAR DEFAULT '2025-26';
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'unit_expenditure' AND column_name = 'fiscal_year'
    ) THEN
        ALTER TABLE unit_expenditure ADD COLUMN fiscal_year VARCHAR DEFAULT '2025-26';
    END IF;
END $$;

UPDATE budget_post_details SET fiscal_year = '2025-26' WHERE fiscal_year IS NULL;
UPDATE post_status SET fiscal_year = '2025-26' WHERE fiscal_year IS NULL;
UPDATE post_expenses SET fiscal_year = '2025-26' WHERE fiscal_year IS NULL;
UPDATE unit_expenditure SET fiscal_year = '2025-26' WHERE fiscal_year IS NULL;

ALTER TABLE budget_post_details ALTER COLUMN fiscal_year SET NOT NULL;
ALTER TABLE post_status ALTER COLUMN fiscal_year SET NOT NULL;
ALTER TABLE post_expenses ALTER COLUMN fiscal_year SET NOT NULL;
ALTER TABLE unit_expenditure ALTER COLUMN fiscal_year SET NOT NULL;

