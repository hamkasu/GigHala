-- Migration 057 (SQLite): Add support system SLA tracking fields

-- SQLite doesn't support ADD COLUMN IF NOT EXISTS before version 3.35,
-- so these are written to be safe to run once.

ALTER TABLE support_ticket ADD COLUMN channel VARCHAR(20) DEFAULT 'web';
ALTER TABLE support_ticket ADD COLUMN sla_due_at DATETIME;
ALTER TABLE support_ticket ADD COLUMN first_responded_at DATETIME;
ALTER TABLE support_ticket ADD COLUMN sla_warning_sent BOOLEAN DEFAULT 0;
ALTER TABLE support_ticket ADD COLUMN sla_breached BOOLEAN DEFAULT 0;
ALTER TABLE support_ticket ADD COLUMN sla_breach_notified BOOLEAN DEFAULT 0;

-- Migrate existing 'payment' category tickets to 'billing'
UPDATE support_ticket SET category = 'billing' WHERE category = 'payment';
