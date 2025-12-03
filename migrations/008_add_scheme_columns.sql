-- Migration: Add scheme_code and sub_scheme_code columns to budget tables
-- Default to 20530028 for backward compatibility with existing data

-- Budget Post Details
ALTER TABLE budget_post_details 
ADD COLUMN IF NOT EXISTS scheme_code VARCHAR(10) DEFAULT '2053',
ADD COLUMN IF NOT EXISTS sub_scheme_code VARCHAR(15) DEFAULT '20530028';

-- Post Status
ALTER TABLE post_status 
ADD COLUMN IF NOT EXISTS scheme_code VARCHAR(10) DEFAULT '2053',
ADD COLUMN IF NOT EXISTS sub_scheme_code VARCHAR(15) DEFAULT '20530028';

-- Post Expenses
ALTER TABLE post_expenses 
ADD COLUMN IF NOT EXISTS scheme_code VARCHAR(10) DEFAULT '2053',
ADD COLUMN IF NOT EXISTS sub_scheme_code VARCHAR(15) DEFAULT '20530028';

-- Unit Expenditure
ALTER TABLE unit_expenditure 
ADD COLUMN IF NOT EXISTS scheme_code VARCHAR(10) DEFAULT '2053',
ADD COLUMN IF NOT EXISTS sub_scheme_code VARCHAR(15) DEFAULT '20530028';

-- Drop old unique constraints (if exist) and create new ones with sub_scheme_code
DO $$
BEGIN
    -- BudgetPostDetails
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_budget_post_natural_key') THEN
        ALTER TABLE budget_post_details DROP CONSTRAINT uq_budget_post_natural_key;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_budget_post_natural_key_v2') THEN
        ALTER TABLE budget_post_details ADD CONSTRAINT uq_budget_post_natural_key_v2 
            UNIQUE (fiscal_year, sub_scheme_code, district, category, class_type, designation);
    END IF;

    -- PostStatus
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_post_status_natural_key') THEN
        ALTER TABLE post_status DROP CONSTRAINT uq_post_status_natural_key;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_post_status_natural_key_v2') THEN
        ALTER TABLE post_status ADD CONSTRAINT uq_post_status_natural_key_v2 
            UNIQUE (fiscal_year, sub_scheme_code, district, category, class_type, status);
    END IF;

    -- PostExpenses
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_post_expenses_natural_key') THEN
        ALTER TABLE post_expenses DROP CONSTRAINT uq_post_expenses_natural_key;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_post_expenses_natural_key_v2') THEN
        ALTER TABLE post_expenses ADD CONSTRAINT uq_post_expenses_natural_key_v2 
            UNIQUE (fiscal_year, sub_scheme_code, district, category, class_type);
    END IF;

    -- UnitExpenditure
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_unit_expenditure_natural_key') THEN
        ALTER TABLE unit_expenditure DROP CONSTRAINT uq_unit_expenditure_natural_key;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_unit_expenditure_natural_key_v2') THEN
        ALTER TABLE unit_expenditure ADD CONSTRAINT uq_unit_expenditure_natural_key_v2 
            UNIQUE (fiscal_year, sub_scheme_code, district, unit_account);
    END IF;
END $$;

-- Create indexes for scheme filtering
CREATE INDEX IF NOT EXISTS idx_bpd_scheme ON budget_post_details(scheme_code, sub_scheme_code);
CREATE INDEX IF NOT EXISTS idx_ps_scheme ON post_status(scheme_code, sub_scheme_code);
CREATE INDEX IF NOT EXISTS idx_pe_scheme ON post_expenses(scheme_code, sub_scheme_code);
CREATE INDEX IF NOT EXISTS idx_ue_scheme ON unit_expenditure(scheme_code, sub_scheme_code);

-- Composite indexes for common queries (fiscal_year + scheme)
CREATE INDEX IF NOT EXISTS idx_bpd_fy_scheme ON budget_post_details(fiscal_year, sub_scheme_code);
CREATE INDEX IF NOT EXISTS idx_ps_fy_scheme ON post_status(fiscal_year, sub_scheme_code);
CREATE INDEX IF NOT EXISTS idx_pe_fy_scheme ON post_expenses(fiscal_year, sub_scheme_code);
CREATE INDEX IF NOT EXISTS idx_ue_fy_scheme ON unit_expenditure(fiscal_year, sub_scheme_code);
