-- Migration: Add post_level_details table for multi-level data entry
-- Purpose: Store individual level details within each budget post
-- The main budget_post_details table will contain aggregated sums
-- Note: This table is shared across all subschemes (uses table_name and sub_scheme_code for isolation)
-- If the table already exists (created by s2053 migration), this will be a no-op due to IF NOT EXISTS

CREATE TABLE IF NOT EXISTS post_level_details (
    id SERIAL PRIMARY KEY,
    
    -- Link to parent budget post (generic - works across subschemes)
    table_name VARCHAR(100) NOT NULL,
    budget_post_id INTEGER NOT NULL,
    sub_scheme_code VARCHAR(15) NOT NULL,
    fiscal_year CHAR(7) NOT NULL DEFAULT '2025-26',
    
    -- Level identification
    level_name VARCHAR(100) NOT NULL,
    level_order INTEGER NOT NULL DEFAULT 1,
    
    -- Pay Matrix selection (stored for reference)
    pay_stage VARCHAR(5),
    pay_level INTEGER,
    
    -- Salary components (stored in thousands like main table)
    special_pay BIGINT NOT NULL DEFAULT 0,
    basic_pay NUMERIC(10, 1) NOT NULL DEFAULT 0,
    grade_pay BIGINT NOT NULL DEFAULT 0,
    
    -- Allowances (stored in thousands)
    local_supplementary_allowance BIGINT NOT NULL DEFAULT 0,
    vehicle_allowance BIGINT NOT NULL DEFAULT 0,
    washing_allowance BIGINT NOT NULL DEFAULT 0,
    cash_allowance BIGINT NOT NULL DEFAULT 0,
    footwear_allowance_other BIGINT NOT NULL DEFAULT 0,
    
    -- HRA configuration
    hra_rate CHAR(1) NOT NULL DEFAULT 'X',
    
    -- Audit fields
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT chk_pld_hra_rate CHECK (hra_rate IN ('X', 'Y', 'Z')),
    CONSTRAINT chk_pld_basic_pay CHECK (basic_pay >= 0),
    CONSTRAINT chk_pld_level_order CHECK (level_order > 0),
    
    -- Unique: one level name per budget post per subscheme
    CONSTRAINT uq_pld_level_name UNIQUE (table_name, budget_post_id, sub_scheme_code, level_name)
);

-- Indexes for performance (only create if they don't exist)
CREATE INDEX IF NOT EXISTS idx_pld_budget_post ON post_level_details(table_name, budget_post_id);
CREATE INDEX IF NOT EXISTS idx_pld_subscheme ON post_level_details(sub_scheme_code);
CREATE INDEX IF NOT EXISTS idx_pld_fiscal_year ON post_level_details(fiscal_year);
CREATE INDEX IF NOT EXISTS idx_pld_order ON post_level_details(budget_post_id, level_order);

-- Trigger to update updated_at timestamp (only create if function doesn't exist)
CREATE OR REPLACE FUNCTION update_post_level_details_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Drop trigger if exists, then recreate (idempotent)
DROP TRIGGER IF EXISTS trg_pld_update_timestamp ON post_level_details;
CREATE TRIGGER trg_pld_update_timestamp
    BEFORE UPDATE ON post_level_details
    FOR EACH ROW
    EXECUTE FUNCTION update_post_level_details_timestamp();

COMMENT ON TABLE post_level_details IS 'Stores individual level entries for budget posts - aggregates to parent table';
COMMENT ON COLUMN post_level_details.table_name IS 'Parent table name (e.g., budget_post_details_20290046)';
COMMENT ON COLUMN post_level_details.budget_post_id IS 'ID of parent budget post record';
COMMENT ON COLUMN post_level_details.level_name IS 'User-provided name for this level';
COMMENT ON COLUMN post_level_details.level_order IS 'Display order (1, 2, 3, ...)';
