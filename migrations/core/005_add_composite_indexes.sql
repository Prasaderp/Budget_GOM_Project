-- Migration: 005_add_composite_indexes.sql
-- Status: Partially OBSOLETE - keeping only valid indexes for shared tables

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
