-- Migration: Add freelancer invoice submission tracking (SQLite)
-- Date: 2025-12-19
-- Description: Adds fields to Invoice table to track when freelancers submit their invoices

-- Add freelancer invoice submission fields to invoice table
ALTER TABLE invoice ADD COLUMN invoice_submitted INTEGER DEFAULT 0;
ALTER TABLE invoice ADD COLUMN freelancer_invoice_number TEXT;
ALTER TABLE invoice ADD COLUMN freelancer_invoice_date TEXT;
ALTER TABLE invoice ADD COLUMN freelancer_submitted_at TEXT;
ALTER TABLE invoice ADD COLUMN freelancer_invoice_file TEXT;
ALTER TABLE invoice ADD COLUMN freelancer_invoice_notes TEXT;

-- Add index for faster queries on submitted invoices
CREATE INDEX IF NOT EXISTS idx_invoice_submitted ON invoice(invoice_submitted);
CREATE INDEX IF NOT EXISTS idx_invoice_freelancer_submitted_at ON invoice(freelancer_submitted_at);
