-- fractional employment feature: 2025
-- adds monthly retainer tracking and termination notice fields to the escrow table

ALTER TABLE escrow ADD COLUMN IF NOT EXISTS retainer_start_date TIMESTAMP;
ALTER TABLE escrow ADD COLUMN IF NOT EXISTS retainer_next_due TIMESTAMP;
ALTER TABLE escrow ADD COLUMN IF NOT EXISTS termination_requested BOOLEAN DEFAULT FALSE;
ALTER TABLE escrow ADD COLUMN IF NOT EXISTS termination_requested_by VARCHAR(20);
ALTER TABLE escrow ADD COLUMN IF NOT EXISTS termination_notice_date TIMESTAMP;
