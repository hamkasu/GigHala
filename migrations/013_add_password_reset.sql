-- Migration: Add password reset fields to User table
-- Date: 2026-01-01
-- Description: Adds password reset token and expiration fields to support forgot password functionality

-- Add password reset token field
ALTER TABLE "user" ADD COLUMN password_reset_token VARCHAR(100);

-- Add password reset expiration field
ALTER TABLE "user" ADD COLUMN password_reset_expires TIMESTAMP;

-- Add index on password_reset_token for faster lookups
CREATE INDEX idx_user_password_reset_token ON "user"(password_reset_token);

-- Note: Password reset tokens will expire after 24 hours
-- Tokens are generated using secrets.token_urlsafe(32) for security
