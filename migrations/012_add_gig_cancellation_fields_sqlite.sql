-- SQLite Migration: Add cancellation tracking fields to Gig table
-- Description: Adds cancellation_reason and cancelled_at fields to support gig cancellation workflow
-- Date: 2025-12-31

-- Add cancellation_reason field
ALTER TABLE gig ADD COLUMN cancellation_reason TEXT;

-- Add cancelled_at timestamp field
ALTER TABLE gig ADD COLUMN cancelled_at DATETIME;

-- Add index for cancelled_at for better query performance
CREATE INDEX idx_gig_cancelled_at ON gig(cancelled_at);

-- Add index for status to optimize cancellation queries
CREATE INDEX IF NOT EXISTS idx_gig_status ON gig(status);
