-- Migration: Add SOCSO Portal Submission Tracking
-- Description: Add fields to track which users have been submitted to SOCSO ASSIST Portal
-- Date: 2025-12-25

-- Add SOCSO portal submission tracking fields to User table
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS socso_submitted_to_portal BOOLEAN DEFAULT FALSE;
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS socso_portal_submission_date TIMESTAMP;
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS socso_portal_reference_number VARCHAR(50);

-- Add indexes for queries
CREATE INDEX IF NOT EXISTS idx_user_socso_submitted ON "user"(socso_submitted_to_portal);
CREATE INDEX IF NOT EXISTS idx_user_socso_portal_date ON "user"(socso_portal_submission_date);

-- Add comment for documentation
COMMENT ON COLUMN "user".socso_submitted_to_portal IS 'Whether user registration has been submitted to SOCSO ASSIST Portal';
COMMENT ON COLUMN "user".socso_portal_submission_date IS 'Date when user was submitted to SOCSO portal';
COMMENT ON COLUMN "user".socso_portal_reference_number IS 'Reference number received from SOCSO portal after submission';
