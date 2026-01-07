-- Migration: Add DA (Dearness Allowance) percentage configuration to fiscal_years
-- Description: Allows client to configure DA percentage per fiscal year instead of hardcoded 64%
-- Default: 64.00% (maintains existing behavior)
-- Version: 012
-- Created: 2026-01-07

-- Add da_percentage column with default 64% and constraints
ALTER TABLE fiscal_years 
ADD COLUMN IF NOT EXISTS da_percentage DECIMAL(5,2) NOT NULL DEFAULT 64.00;

-- Add check constraint to ensure DA percentage is within valid range (0-100%)
ALTER TABLE fiscal_years 
ADD CONSTRAINT chk_fiscal_years_da_percentage 
CHECK (da_percentage >= 0 AND da_percentage <= 100);

-- Create index for optimized queries on da_percentage
CREATE INDEX IF NOT EXISTS ix_fiscal_years_da_percentage 
ON fiscal_years(da_percentage);

-- Update existing records to default 64% if NULL (defensive measure)
UPDATE fiscal_years 
SET da_percentage = 64.00 
WHERE da_percentage IS NULL;
