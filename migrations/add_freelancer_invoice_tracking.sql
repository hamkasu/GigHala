-- Migration: Add freelancer invoice submission tracking
-- Date: 2025-12-19
-- Description: Adds fields to Invoice table to track when freelancers submit their invoices

-- Add freelancer invoice submission fields to invoice table
ALTER TABLE invoice ADD COLUMN invoice_submitted BOOLEAN DEFAULT FALSE;
ALTER TABLE invoice ADD COLUMN freelancer_invoice_number VARCHAR(100);
ALTER TABLE invoice ADD COLUMN freelancer_invoice_date TIMESTAMP;
ALTER TABLE invoice ADD COLUMN freelancer_submitted_at TIMESTAMP;
ALTER TABLE invoice ADD COLUMN freelancer_invoice_file VARCHAR(255);
ALTER TABLE invoice ADD COLUMN freelancer_invoice_notes TEXT;

-- Add index for faster queries on submitted invoices
CREATE INDEX idx_invoice_submitted ON invoice(invoice_submitted);
CREATE INDEX idx_invoice_freelancer_submitted_at ON invoice(freelancer_submitted_at);
