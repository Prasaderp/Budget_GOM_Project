-- Migration: Add hra_rate column to budget_post_details table
-- X = 30%, Y = 20%, Z = 10%

ALTER TABLE budget_post_details 
ADD COLUMN IF NOT EXISTS hra_rate CHAR(1) NOT NULL DEFAULT 'X';

ALTER TABLE budget_post_details 
ADD CONSTRAINT chk_hra_rate_valid CHECK (hra_rate IN ('X', 'Y', 'Z'));

