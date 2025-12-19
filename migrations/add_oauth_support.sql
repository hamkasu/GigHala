-- Database Migration: Add OAuth Support
-- Date: 2025-12-19
-- Description: Adds OAuth provider fields to User table for social login support

-- Add OAuth provider fields to user table
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS oauth_provider VARCHAR(20);
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS oauth_id VARCHAR(255);

-- Make password_hash nullable for OAuth users
ALTER TABLE "user" ALTER COLUMN password_hash DROP NOT NULL;

-- Create index for faster OAuth lookups
CREATE INDEX IF NOT EXISTS idx_user_oauth_provider_id ON "user"(oauth_provider, oauth_id);

-- Comments
COMMENT ON COLUMN "user".oauth_provider IS 'OAuth provider: google, apple, microsoft, or null for regular users';
COMMENT ON COLUMN "user".oauth_id IS 'User ID from OAuth provider';
