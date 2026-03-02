-- Migration: Create district_expenditure_2215 table
-- Scheme: 2215 - Water Scarcity
-- Sub-scheme: 2215 - Water Scarcity (with account heads)

CREATE TABLE IF NOT EXISTS district_expenditure_2215 (
    id SERIAL PRIMARY KEY,
    fiscal_year CHAR(7) NOT NULL,
    scheme_code VARCHAR(10) NOT NULL DEFAULT '2215',
    sub_scheme_code VARCHAR(15) NOT NULL DEFAULT '2215',
    account_head_code VARCHAR(20) NOT NULL,
    district VARCHAR(100) NOT NULL,
    expenditure_prev3 BIGINT NOT NULL DEFAULT 0,
    expenditure_prev2 BIGINT NOT NULL DEFAULT 0,
    expenditure_prev1 BIGINT NOT NULL DEFAULT 0,
    budget_estimate_curr BIGINT NOT NULL DEFAULT 0,
    revised_demand_curr BIGINT NOT NULL DEFAULT 0,
    budget_estimate_next BIGINT NOT NULL DEFAULT 0,
    remarks VARCHAR(500),
    CONSTRAINT uq_district_exp_2215_natural_key UNIQUE (fiscal_year, sub_scheme_code, account_head_code, district),
    CONSTRAINT chk_exp_prev3_non_negative_2215 CHECK (expenditure_prev3 >= 0),
    CONSTRAINT chk_exp_prev2_non_negative_2215 CHECK (expenditure_prev2 >= 0),
    CONSTRAINT chk_exp_prev1_non_negative_2215 CHECK (expenditure_prev1 >= 0),
    CONSTRAINT chk_be_curr_non_negative_2215 CHECK (budget_estimate_curr >= 0),
    CONSTRAINT chk_revised_demand_curr_non_negative_2215 CHECK (revised_demand_curr >= 0),
    CONSTRAINT chk_be_next_non_negative_2215 CHECK (budget_estimate_next >= 0)
);

-- Create indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_district_exp_2215_fiscal_year ON district_expenditure_2215(fiscal_year);
CREATE INDEX IF NOT EXISTS idx_district_exp_2215_scheme_code ON district_expenditure_2215(scheme_code);
CREATE INDEX IF NOT EXISTS idx_district_exp_2215_sub_scheme_code ON district_expenditure_2215(sub_scheme_code);
CREATE INDEX IF NOT EXISTS idx_district_exp_2215_account_head_code ON district_expenditure_2215(account_head_code);
CREATE INDEX IF NOT EXISTS idx_district_exp_2215_district ON district_expenditure_2215(district);
CREATE INDEX IF NOT EXISTS idx_district_exp_2215_fy_account_district ON district_expenditure_2215(fiscal_year, account_head_code, district);

