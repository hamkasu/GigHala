-- Migration: Add Two-Factor Authentication (2FA) Support
-- Database: PostgreSQL
-- Date: 2025-12-24
-- Description: Adds TOTP-based 2FA fields to the User table for enhanced security

-- Add 2FA columns to user table
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS totp_secret VARCHAR(32);
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS totp_enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS totp_enabled_at TIMESTAMP;

-- Create index on totp_enabled for efficient queries
CREATE INDEX IF NOT EXISTS idx_user_totp_enabled ON "user"(totp_enabled);

-- Add comment to columns for documentation
COMMENT ON COLUMN "user".totp_secret IS 'TOTP secret key for Two-Factor Authentication';
COMMENT ON COLUMN "user".totp_enabled IS 'Whether Two-Factor Authentication is enabled for this user';
COMMENT ON COLUMN "user".totp_enabled_at IS 'Timestamp when 2FA was enabled';
