-- Migration: Add email verification fields to User table
-- Date: 2026-01-01
-- Description: Adds email verification token and expiration fields to support email verification during registration

-- Add email verification token field
ALTER TABLE "user" ADD COLUMN email_verification_token VARCHAR(100);

-- Add email verification expiration field
ALTER TABLE "user" ADD COLUMN email_verification_expires TIMESTAMP;

-- Add index on email_verification_token for faster lookups
CREATE INDEX idx_user_email_verification_token ON "user"(email_verification_token);

-- Note: OAuth users (Google, Microsoft, Apple) are already set as is_verified=True during registration
-- Regular email/password users will need to verify their email address via the verification link
