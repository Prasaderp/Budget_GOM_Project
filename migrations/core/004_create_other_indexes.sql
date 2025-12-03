-- Migration: Create other performance indexes
-- Version: 004_create_other_indexes.sql
-- Description: Creates indexes for messages, assistant_chats, users, admin_users

CREATE INDEX IF NOT EXISTS idx_messages_thread ON messages(thread_key);
CREATE INDEX IF NOT EXISTS idx_messages_from_to ON messages(from_username, to_username, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_assistant_chats_user_created ON assistant_chats(username, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_users_username_active ON users(username, is_active);
CREATE INDEX IF NOT EXISTS idx_admin_username ON admin_users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email) WHERE email IS NOT NULL;

