-- Migration: Add SOCSO Registration Fields (SQLite)
-- Description: Add additional fields required for complete SOCSO registration under SESKSO (Gig Workers Bill 2025)
-- Date: 2025-12-25

-- Add SOCSO registration fields to User table
ALTER TABLE user ADD COLUMN date_of_birth TEXT;  -- SQLite uses TEXT for dates
ALTER TABLE user ADD COLUMN gender TEXT;
ALTER TABLE user ADD COLUMN marital_status TEXT;
ALTER TABLE user ADD COLUMN nationality TEXT DEFAULT 'Malaysian';
ALTER TABLE user ADD COLUMN race TEXT;
ALTER TABLE user ADD COLUMN address_line1 TEXT;
ALTER TABLE user ADD COLUMN address_line2 TEXT;
ALTER TABLE user ADD COLUMN postcode TEXT;
ALTER TABLE user ADD COLUMN city TEXT;
ALTER TABLE user ADD COLUMN state TEXT;
ALTER TABLE user ADD COLUMN country TEXT DEFAULT 'Malaysia';
ALTER TABLE user ADD COLUMN self_employment_start_date TEXT;  -- SQLite uses TEXT for dates
ALTER TABLE user ADD COLUMN monthly_income_range TEXT;
ALTER TABLE user ADD COLUMN socso_registration_date TEXT;  -- SQLite uses TEXT for datetime

-- Add indexes for common queries
CREATE INDEX IF NOT EXISTS idx_user_state ON user(state);
CREATE INDEX IF NOT EXISTS idx_user_city ON user(city);
CREATE INDEX IF NOT EXISTS idx_user_socso_registered ON user(socso_registered);
CREATE INDEX IF NOT EXISTS idx_user_socso_data_complete ON user(socso_data_complete);
