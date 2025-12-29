-- Migration: Add partial refund support to Escrow table
-- Date: 2025-12-29
-- Description: Track refunded amounts for partial refund functionality

-- Add refunded_amount column to escrow table
ALTER TABLE escrow ADD COLUMN IF NOT EXISTS refunded_amount FLOAT DEFAULT 0.0;

-- Set default value for existing records
UPDATE escrow SET refunded_amount = 0.0 WHERE refunded_amount IS NULL;

-- Update refunded escrows to have full amount marked as refunded
UPDATE escrow SET refunded_amount = amount WHERE status = 'refunded' AND refunded_amount = 0.0;
