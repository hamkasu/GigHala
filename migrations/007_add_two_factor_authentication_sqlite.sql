-- Migration: Add Two-Factor Authentication (2FA) Support
-- Database: SQLite
-- Date: 2025-12-24
-- Description: Adds TOTP-based 2FA fields to the User table for enhanced security

-- Note: SQLite doesn't support ADD COLUMN IF NOT EXISTS before version 3.35.0
-- These statements will fail if columns already exist, which is expected behavior

-- Add 2FA columns to user table
ALTER TABLE user ADD COLUMN totp_secret VARCHAR(32);
ALTER TABLE user ADD COLUMN totp_enabled BOOLEAN DEFAULT 0;
ALTER TABLE user ADD COLUMN totp_enabled_at TIMESTAMP;

-- Create index on totp_enabled for efficient queries
CREATE INDEX IF NOT EXISTS idx_user_totp_enabled ON user(totp_enabled);
