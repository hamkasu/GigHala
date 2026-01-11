-- Add Stripe Connect fields to User table for Instant Payouts
-- This enables freelancers to connect their Malaysian bank accounts for instant payouts

ALTER TABLE user ADD COLUMN IF NOT EXISTS stripe_account_id VARCHAR(255) UNIQUE;
ALTER TABLE user ADD COLUMN IF NOT EXISTS stripe_account_status VARCHAR(50); -- 'pending', 'active', 'restricted', 'rejected'
ALTER TABLE user ADD COLUMN IF NOT EXISTS stripe_onboarding_completed BOOLEAN DEFAULT FALSE;
ALTER TABLE user ADD COLUMN IF NOT EXISTS instant_payout_enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE user ADD COLUMN IF NOT EXISTS stripe_account_created_at TIMESTAMP;

-- Add instant payout tracking to Payout table
ALTER TABLE payout ADD COLUMN IF NOT EXISTS is_instant BOOLEAN DEFAULT FALSE;
ALTER TABLE payout ADD COLUMN IF NOT EXISTS stripe_payout_id VARCHAR(255) UNIQUE;
ALTER TABLE payout ADD COLUMN IF NOT EXISTS estimated_arrival TIMESTAMP;

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_user_stripe_account_id ON user(stripe_account_id);
CREATE INDEX IF NOT EXISTS idx_payout_stripe_payout_id ON payout(stripe_payout_id);
