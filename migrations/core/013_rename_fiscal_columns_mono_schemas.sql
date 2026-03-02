DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'district_revenue_0029' AND column_name = 'actual_2017_18'
    ) THEN
        ALTER TABLE district_revenue_0029 RENAME COLUMN actual_2017_18 TO actual_prev3;
        ALTER TABLE district_revenue_0029 RENAME COLUMN actual_2018_19 TO actual_prev2;
        ALTER TABLE district_revenue_0029 RENAME COLUMN actual_2019_20 TO actual_prev1;
        ALTER TABLE district_revenue_0029 RENAME COLUMN budget_estimate_2020_21 TO budget_estimate_curr;
        ALTER TABLE district_revenue_0029 RENAME COLUMN revised_estimate_2020_21 TO revised_estimate_curr;
        ALTER TABLE district_revenue_0029 RENAME COLUMN budget_estimate_2021_22 TO budget_estimate_next;
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'sub_head_expenditure_2075' AND column_name = 'expenditure_2022_23'
    ) THEN
        ALTER TABLE sub_head_expenditure_2075 RENAME COLUMN expenditure_2022_23 TO expenditure_prev3;
        ALTER TABLE sub_head_expenditure_2075 RENAME COLUMN expenditure_2023_24 TO expenditure_prev2;
        ALTER TABLE sub_head_expenditure_2075 RENAME COLUMN expenditure_2024_25 TO expenditure_prev1;
        ALTER TABLE sub_head_expenditure_2075 RENAME COLUMN budget_estimate TO budget_estimate_curr;
        ALTER TABLE sub_head_expenditure_2075 RENAME COLUMN revised_estimate TO revised_estimate_curr;
        ALTER TABLE sub_head_expenditure_2075 RENAME COLUMN budget_estimate_2026_27 TO budget_estimate_next;
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'district_expenditure_2075' AND column_name = 'expenditure_2022_23'
    ) THEN
        ALTER TABLE district_expenditure_2075 RENAME COLUMN expenditure_2022_23 TO expenditure_prev3;
        ALTER TABLE district_expenditure_2075 RENAME COLUMN expenditure_2023_24 TO expenditure_prev2;
        ALTER TABLE district_expenditure_2075 RENAME COLUMN expenditure_2024_25 TO expenditure_prev1;
        ALTER TABLE district_expenditure_2075 RENAME COLUMN budget_estimate TO budget_estimate_curr;
        ALTER TABLE district_expenditure_2075 RENAME COLUMN revised_estimate TO revised_estimate_curr;
        ALTER TABLE district_expenditure_2075 RENAME COLUMN budget_estimate_2026_27 TO budget_estimate_next;
    END IF;
END $$;
