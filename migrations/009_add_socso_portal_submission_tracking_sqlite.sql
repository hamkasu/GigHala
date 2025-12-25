-- Migration: Add SOCSO Portal Submission Tracking (SQLite)
-- Description: Add fields to track which users have been submitted to SOCSO ASSIST Portal
-- Date: 2025-12-25

-- Add SOCSO portal submission tracking fields to User table
ALTER TABLE user ADD COLUMN socso_submitted_to_portal INTEGER DEFAULT 0;  -- SQLite uses INTEGER for boolean
ALTER TABLE user ADD COLUMN socso_portal_submission_date TEXT;  -- SQLite uses TEXT for datetime
ALTER TABLE user ADD COLUMN socso_portal_reference_number TEXT;

-- Add indexes for queries
CREATE INDEX IF NOT EXISTS idx_user_socso_submitted ON user(socso_submitted_to_portal);
CREATE INDEX IF NOT EXISTS idx_user_socso_portal_date ON user(socso_portal_submission_date);
