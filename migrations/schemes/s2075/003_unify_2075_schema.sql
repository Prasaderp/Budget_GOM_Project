-- ==========================================
-- Migration: Unify 2075 schema
-- Consolidates separate subscheme tables into unified naming structure
-- Migrates data from old tables to new unified tables (created by SQLAlchemy)
-- Safe to run multiple times - handles all edge cases
-- ==========================================

DO $$
BEGIN
    -- Migrate sub_head_expenditure_20750249 -> sub_head_expenditure_2075
    IF EXISTS (SELECT 1 FROM information_schema.tables 
               WHERE table_schema = 'public' AND table_name = 'sub_head_expenditure_20750249') THEN
        
        INSERT INTO sub_head_expenditure_2075 (
            fiscal_year, scheme_code, sub_scheme_code, sub_head,
            expenditure_2022_23, expenditure_2023_24, expenditure_2024_25,
            budget_estimate, revised_estimate, budget_estimate_2026_27, remarks
        )
        SELECT 
            fiscal_year, scheme_code, sub_scheme_code, sub_head,
            expenditure_2022_23, expenditure_2023_24, expenditure_2024_25,
            budget_estimate, revised_estimate, budget_estimate_2026_27, remarks
        FROM sub_head_expenditure_20750249
        ON CONFLICT (fiscal_year, sub_scheme_code, sub_head) DO NOTHING;
        
        DROP TABLE sub_head_expenditure_20750249;
        RAISE NOTICE 'Migrated and dropped sub_head_expenditure_20750249';
    END IF;

    -- Migrate district_expenditure_20750294 -> district_expenditure_2075
    IF EXISTS (SELECT 1 FROM information_schema.tables 
               WHERE table_schema = 'public' AND table_name = 'district_expenditure_20750294') THEN
        
        INSERT INTO district_expenditure_2075 (
            fiscal_year, scheme_code, sub_scheme_code, district,
            expenditure_2022_23, expenditure_2023_24, expenditure_2024_25,
            budget_estimate, revised_estimate, budget_estimate_2026_27, remarks
        )
        SELECT 
            fiscal_year, scheme_code, sub_scheme_code, district,
            expenditure_2022_23, expenditure_2023_24, expenditure_2024_25,
            budget_estimate, revised_estimate, budget_estimate_2026_27, remarks
        FROM district_expenditure_20750294
        ON CONFLICT (fiscal_year, sub_scheme_code, district) DO NOTHING;
        
        DROP TABLE district_expenditure_20750294;
        RAISE NOTICE 'Migrated and dropped district_expenditure_20750294';
    END IF;
END $$;
