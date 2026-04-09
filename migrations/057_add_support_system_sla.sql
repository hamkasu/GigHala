-- Migration 057: Add support system SLA tracking fields
-- Adds SLA columns to support_ticket table and renames 'payment' category to 'billing'

-- Add SLA tracking columns to support_ticket
ALTER TABLE support_ticket ADD COLUMN IF NOT EXISTS channel VARCHAR(20) DEFAULT 'web';
ALTER TABLE support_ticket ADD COLUMN IF NOT EXISTS sla_due_at TIMESTAMP;
ALTER TABLE support_ticket ADD COLUMN IF NOT EXISTS first_responded_at TIMESTAMP;
ALTER TABLE support_ticket ADD COLUMN IF NOT EXISTS sla_warning_sent BOOLEAN DEFAULT FALSE;
ALTER TABLE support_ticket ADD COLUMN IF NOT EXISTS sla_breached BOOLEAN DEFAULT FALSE;
ALTER TABLE support_ticket ADD COLUMN IF NOT EXISTS sla_breach_notified BOOLEAN DEFAULT FALSE;

-- Migrate existing 'payment' category tickets to 'billing'
UPDATE support_ticket SET category = 'billing' WHERE category = 'payment';

-- Backfill sla_due_at for existing open/in_progress tickets (8-hour default for medium priority)
UPDATE support_ticket
SET sla_due_at = created_at + INTERVAL '8 hours'
WHERE sla_due_at IS NULL
  AND status IN ('open', 'in_progress', 'escalated')
  AND priority = 'medium';

UPDATE support_ticket
SET sla_due_at = created_at + INTERVAL '4 hours'
WHERE sla_due_at IS NULL
  AND status IN ('open', 'in_progress', 'escalated')
  AND priority IN ('high', 'urgent');

UPDATE support_ticket
SET sla_due_at = created_at + INTERVAL '24 hours'
WHERE sla_due_at IS NULL
  AND status IN ('open', 'in_progress', 'escalated')
  AND priority = 'low';

-- Mark already-breached tickets (created more than their SLA window ago, still open)
UPDATE support_ticket
SET sla_breached = TRUE
WHERE sla_due_at IS NOT NULL
  AND sla_due_at < NOW()
  AND status IN ('open', 'in_progress', 'escalated');
