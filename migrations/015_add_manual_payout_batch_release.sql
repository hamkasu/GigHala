-- Migration: Add manual payout batch release fields
-- Description: Adds fields to support manual payout release batches at 8am and 4pm
-- Date: 2026-01-12

-- Add manual release batch fields to payout table
ALTER TABLE payout ADD COLUMN IF NOT EXISTS scheduled_release_time TIMESTAMP;
ALTER TABLE payout ADD COLUMN IF NOT EXISTS release_batch VARCHAR(50);
ALTER TABLE payout ADD COLUMN IF NOT EXISTS ready_for_release BOOLEAN DEFAULT FALSE;
ALTER TABLE payout ADD COLUMN IF NOT EXISTS ready_for_release_at TIMESTAMP;
ALTER TABLE payout ADD COLUMN IF NOT EXISTS ready_for_release_by INTEGER REFERENCES "user"(id);
ALTER TABLE payout ADD COLUMN IF NOT EXISTS external_payment_confirmed BOOLEAN DEFAULT FALSE;
ALTER TABLE payout ADD COLUMN IF NOT EXISTS external_payment_confirmed_at TIMESTAMP;
ALTER TABLE payout ADD COLUMN IF NOT EXISTS external_payment_confirmed_by INTEGER REFERENCES "user"(id);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_payout_release_batch ON payout(release_batch);
CREATE INDEX IF NOT EXISTS idx_payout_scheduled_release_time ON payout(scheduled_release_time);
CREATE INDEX IF NOT EXISTS idx_payout_ready_for_release ON payout(ready_for_release) WHERE ready_for_release = TRUE;
CREATE INDEX IF NOT EXISTS idx_payout_external_payment_confirmed ON payout(external_payment_confirmed) WHERE external_payment_confirmed = TRUE;

-- Add comments for documentation
COMMENT ON COLUMN payout.scheduled_release_time IS 'Scheduled batch release time (8am or 4pm Malaysia Time)';
COMMENT ON COLUMN payout.release_batch IS 'Batch identifier (e.g., 2026-01-12-08:00 or 2026-01-12-16:00)';
COMMENT ON COLUMN payout.ready_for_release IS 'Admin marked ready for batch release';
COMMENT ON COLUMN payout.ready_for_release_at IS 'When admin marked it ready';
COMMENT ON COLUMN payout.ready_for_release_by IS 'Admin who marked it ready';
COMMENT ON COLUMN payout.external_payment_confirmed IS 'Admin confirmed external payment done via banking app';
COMMENT ON COLUMN payout.external_payment_confirmed_at IS 'When admin confirmed payment';
COMMENT ON COLUMN payout.external_payment_confirmed_by IS 'Admin who confirmed payment';
