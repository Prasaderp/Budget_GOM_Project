-- Composite indexes for common query patterns to optimize budget summary and details queries

-- BudgetPostDetails composite indexes
CREATE INDEX IF NOT EXISTS idx_budget_post_details_fiscal_district 
    ON budget_post_details(fiscal_year, district);

CREATE INDEX IF NOT EXISTS idx_budget_post_details_fiscal_district_category 
    ON budget_post_details(fiscal_year, district, category);

CREATE INDEX IF NOT EXISTS idx_budget_post_details_fiscal_district_category_class 
    ON budget_post_details(fiscal_year, district, category, class_type);

CREATE INDEX IF NOT EXISTS idx_budget_post_details_fiscal_category_class_designation 
    ON budget_post_details(fiscal_year, category, class_type, designation);

-- PostExpenses composite indexes
CREATE INDEX IF NOT EXISTS idx_post_expenses_fiscal_district 
    ON post_expenses(fiscal_year, district);

CREATE INDEX IF NOT EXISTS idx_post_expenses_fiscal_district_category 
    ON post_expenses(fiscal_year, district, category);

CREATE INDEX IF NOT EXISTS idx_post_expenses_fiscal_category_class 
    ON post_expenses(fiscal_year, category, class_type);

-- PostStatus composite indexes
CREATE INDEX IF NOT EXISTS idx_post_status_fiscal_district 
    ON post_status(fiscal_year, district);

CREATE INDEX IF NOT EXISTS idx_post_status_fiscal_district_category 
    ON post_status(fiscal_year, district, category);

CREATE INDEX IF NOT EXISTS idx_post_status_fiscal_category_class 
    ON post_status(fiscal_year, category, class_type);

-- UnitExpenditure composite index
CREATE INDEX IF NOT EXISTS idx_unit_expenditure_fiscal_district 
    ON unit_expenditure(fiscal_year, district);

-- Message indexes for thread-based queries
CREATE INDEX IF NOT EXISTS idx_messages_thread_created 
    ON messages(thread_key, created_at DESC);

-- AuditLog indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_audit_logs_table_record 
    ON audit_logs(table_name, record_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_audit_logs_user_timestamp 
    ON audit_logs(username, timestamp DESC);

-- User indexes
CREATE INDEX IF NOT EXISTS idx_users_level_unit 
    ON users(level, unit) WHERE is_active = true;

-- Drop redundant single-column indexes that are covered by composite indexes
-- (PostgreSQL can use composite indexes for prefix queries)
-- Keep only if they're used for queries that don't include fiscal_year

