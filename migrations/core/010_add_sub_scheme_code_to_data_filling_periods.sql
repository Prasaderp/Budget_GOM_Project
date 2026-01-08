-- Add sub_scheme_code column to data_filling_periods table
-- This makes timing periods scheme-specific

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'data_filling_periods' AND column_name = 'sub_scheme_code'
    ) THEN
        ALTER TABLE data_filling_periods
        ADD COLUMN sub_scheme_code VARCHAR(15) NOT NULL DEFAULT '20530028';
        
        CREATE INDEX IF NOT EXISTS idx_data_filling_periods_sub_scheme_code 
        ON data_filling_periods(sub_scheme_code);
        
        CREATE INDEX IF NOT EXISTS idx_data_filling_periods_scheme_level_active
        ON data_filling_periods(sub_scheme_code, level, is_active);
    END IF;
END $$;

