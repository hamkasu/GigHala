-- Migration: Add DuitNow QR payment fields to Escrow table
-- Date: 2026-06-20
-- Description: Add fields to support DuitNow QR code payments for Malaysian escrow payments

-- Add DuitNow-specific columns to escrow table
ALTER TABLE escrow ADD COLUMN IF NOT EXISTS payment_method VARCHAR(30) DEFAULT 'bank_transfer';
ALTER TABLE escrow ADD COLUMN IF NOT EXISTS qr_code_image LONGBLOB;
ALTER TABLE escrow ADD COLUMN IF NOT EXISTS qr_code_string TEXT;
ALTER TABLE escrow ADD COLUMN IF NOT EXISTS duitnow_reference VARCHAR(50);
ALTER TABLE escrow ADD COLUMN IF NOT EXISTS payment_confirmation_ref VARCHAR(100);

-- Create index for DuitNow reference lookups
CREATE INDEX IF NOT EXISTS idx_escrow_duitnow_reference ON escrow(duitnow_reference);

-- Create index for payment method queries
CREATE INDEX IF NOT EXISTS idx_escrow_payment_method ON escrow(payment_method);

-- Add comment explaining the fields
ALTER TABLE escrow MODIFY COLUMN payment_method VARCHAR(30) COMMENT 'Payment method: duitnow, fpx, bank_transfer, etc.';
ALTER TABLE escrow MODIFY COLUMN qr_code_image LONGBLOB COMMENT 'QR code image PNG bytes for DuitNow payments';
ALTER TABLE escrow MODIFY COLUMN qr_code_string TEXT COMMENT 'DuitNow EMVCo formatted string used to generate QR code';
ALTER TABLE escrow MODIFY COLUMN duitnow_reference VARCHAR(50) COMMENT 'Unique reference embedded in DuitNow QR code';
ALTER TABLE escrow MODIFY COLUMN payment_confirmation_ref VARCHAR(100) COMMENT 'Client bank reference from DuitNow transaction';
