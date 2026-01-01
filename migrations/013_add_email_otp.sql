-- Migration: Add email OTP verification fields to User table
-- Date: 2026-01-01
-- Description: Adds email OTP code and expiration fields to support OTP-based email verification during registration

-- Add email OTP code field (6-digit code)
ALTER TABLE "user" ADD COLUMN email_otp_code VARCHAR(6);

-- Add email OTP expiration field (10-minute expiry)
ALTER TABLE "user" ADD COLUMN email_otp_expires TIMESTAMP;

-- Add index on email_otp_code for faster lookups
CREATE INDEX idx_user_email_otp_code ON "user"(email_otp_code);

-- Note: This OTP-based verification replaces the token-based system for new registrations
-- OTP codes expire in 10 minutes and are single-use for enhanced security
