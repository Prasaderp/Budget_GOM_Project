-- Migration: Add email, phone_number, and notification_preferences to users table
-- Date: 2024
-- Description: Adds email, phone_number columns and notification_preferences JSON column to users table

-- Add email column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'email'
    ) THEN
        ALTER TABLE users ADD COLUMN email VARCHAR;
        CREATE INDEX IF NOT EXISTS ix_users_email ON users(email);
    END IF;
END $$;

-- Add phone_number column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'phone_number'
    ) THEN
        ALTER TABLE users ADD COLUMN phone_number VARCHAR;
    END IF;
END $$;

-- Add notification_preferences JSON column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'notification_preferences'
    ) THEN
        ALTER TABLE users ADD COLUMN notification_preferences JSON;
    END IF;
END $$;

-- Initialize notification preferences for existing users with NULL values
UPDATE users 
SET notification_preferences = '{"data_filling_period": true, "taluka_activation": true, "fiscal_year_changes": true}'::json
WHERE notification_preferences IS NULL;

