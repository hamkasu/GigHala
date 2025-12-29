-- Migration: Add payment_gateway field to Escrow table
-- Date: 2025-12-29
-- Description: Track which payment gateway (stripe, payhalal, bank_transfer) was used for escrow funding

-- Add payment_gateway column to escrow table
ALTER TABLE escrow ADD COLUMN IF NOT EXISTS payment_gateway VARCHAR(50);

-- Set default gateway for existing records based on payment_reference pattern
-- Stripe payment references start with 'pi_' or 'cs_'
UPDATE escrow
SET payment_gateway = CASE
    WHEN payment_reference LIKE 'pi_%' OR payment_reference LIKE 'cs_%' THEN 'stripe'
    WHEN payment_reference LIKE 'PH%' THEN 'payhalal'
    ELSE 'bank_transfer'
END
WHERE payment_gateway IS NULL;

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_escrow_payment_gateway ON escrow(payment_gateway);
