-- Migration: Add Stripe customer ID to User table
-- Date: 2025-12-29
-- Description: Track Stripe customer IDs for saved payment methods functionality

-- Add stripe_customer_id column to user table
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS stripe_customer_id VARCHAR(100);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_user_stripe_customer_id ON "user"(stripe_customer_id);
