-- Migration: Add manual payout batch release fields (SQLite)
-- Description: Adds fields to support manual payout release batches at 8am and 4pm
-- Date: 2026-01-12

-- Add manual release batch fields to payout table
ALTER TABLE payout ADD COLUMN scheduled_release_time DATETIME;
ALTER TABLE payout ADD COLUMN release_batch VARCHAR(50);
ALTER TABLE payout ADD COLUMN ready_for_release BOOLEAN DEFAULT 0;
ALTER TABLE payout ADD COLUMN ready_for_release_at DATETIME;
ALTER TABLE payout ADD COLUMN ready_for_release_by INTEGER;
ALTER TABLE payout ADD COLUMN external_payment_confirmed BOOLEAN DEFAULT 0;
ALTER TABLE payout ADD COLUMN external_payment_confirmed_at DATETIME;
ALTER TABLE payout ADD COLUMN external_payment_confirmed_by INTEGER;

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_payout_release_batch ON payout(release_batch);
CREATE INDEX IF NOT EXISTS idx_payout_scheduled_release_time ON payout(scheduled_release_time);
CREATE INDEX IF NOT EXISTS idx_payout_ready_for_release ON payout(ready_for_release);
CREATE INDEX IF NOT EXISTS idx_payout_external_payment_confirmed ON payout(external_payment_confirmed);
