-- Migration: Add salary_mode column to fiscal_years table
-- Purpose: Support monthly/annual toggle for salary calculations

-- Add salary_mode column with default 'monthly' for backward compatibility
ALTER TABLE fiscal_years ADD COLUMN IF NOT EXISTS salary_mode VARCHAR(10) NOT NULL DEFAULT 'monthly';

-- Add check constraint to ensure valid values
ALTER TABLE fiscal_years ADD CONSTRAINT chk_fiscal_years_salary_mode 
    CHECK (salary_mode IN ('monthly', 'annual'));

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS ix_fiscal_years_salary_mode ON fiscal_years(salary_mode);

