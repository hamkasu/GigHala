-- Migration 050: Add Specialized Worker Rates
-- Description: Add support for workers to define their own specific charges/rates
-- Date: 2026-02-02
-- Author: Claude Code
--
-- This migration adds:
-- 1. Rate fields to worker_specialization table
-- 2. Specialized rate tracking to gig_worker table
-- 3. Specialized rate reference to application table
--
-- For halal-compliant transparent pricing - no hidden fees

-- ============================================
-- 1. Add rate fields to worker_specialization
-- ============================================

-- Add specialization_title column (custom title like "Senior Quran Tutor")
ALTER TABLE worker_specialization ADD COLUMN IF NOT EXISTS specialization_title VARCHAR(100);

-- Add base_hourly_rate column (MYR per hour)
ALTER TABLE worker_specialization ADD COLUMN IF NOT EXISTS base_hourly_rate DECIMAL(10,2);

-- Add base_fixed_rate column (MYR per fixed gig)
ALTER TABLE worker_specialization ADD COLUMN IF NOT EXISTS base_fixed_rate DECIMAL(10,2);

-- Add premium_multiplier column (default 1.0, e.g., 1.2 = 20% premium)
ALTER TABLE worker_specialization ADD COLUMN IF NOT EXISTS premium_multiplier DECIMAL(3,2) DEFAULT 1.0;

-- ============================================
-- 2. Add specialized rate tracking to gig_worker
-- ============================================

-- Add specialized_rate_used flag for analytics
ALTER TABLE gig_worker ADD COLUMN IF NOT EXISTS specialized_rate_used BOOLEAN DEFAULT FALSE;

-- Add reference to the specialization used
ALTER TABLE gig_worker ADD COLUMN IF NOT EXISTS specialization_id INTEGER REFERENCES worker_specialization(id);

-- ============================================
-- 3. Add specialized rate reference to application
-- ============================================

-- Add flag for when worker uses specialized rate
ALTER TABLE application ADD COLUMN IF NOT EXISTS use_specialized_rate BOOLEAN DEFAULT FALSE;

-- Add reference to the specialization used in application
ALTER TABLE application ADD COLUMN IF NOT EXISTS specialization_id INTEGER REFERENCES worker_specialization(id);

-- ============================================
-- 4. Create indexes for efficient queries
-- ============================================

-- Index for finding workers by rate
CREATE INDEX IF NOT EXISTS idx_worker_spec_hourly_rate ON worker_specialization(base_hourly_rate) WHERE base_hourly_rate IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_worker_spec_fixed_rate ON worker_specialization(base_fixed_rate) WHERE base_fixed_rate IS NOT NULL;

-- Index for filtering workers with specialized rates
CREATE INDEX IF NOT EXISTS idx_worker_spec_has_rates ON worker_specialization(user_id)
WHERE base_hourly_rate IS NOT NULL OR base_fixed_rate IS NOT NULL;

-- Index for analytics on specialized rate usage
CREATE INDEX IF NOT EXISTS idx_gig_worker_specialized ON gig_worker(specialized_rate_used) WHERE specialized_rate_used = TRUE;

-- ============================================
-- 5. Add audit table for rate changes (PDPA compliance)
-- ============================================

CREATE TABLE IF NOT EXISTS worker_rate_audit (
    id SERIAL PRIMARY KEY,
    specialization_id INTEGER REFERENCES worker_specialization(id),
    user_id INTEGER REFERENCES "user"(id),
    field_changed VARCHAR(50) NOT NULL,
    old_value TEXT,
    new_value TEXT,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(45),
    user_agent TEXT
);

-- Index for audit lookups
CREATE INDEX IF NOT EXISTS idx_rate_audit_user ON worker_rate_audit(user_id);
CREATE INDEX IF NOT EXISTS idx_rate_audit_spec ON worker_rate_audit(specialization_id);
CREATE INDEX IF NOT EXISTS idx_rate_audit_date ON worker_rate_audit(changed_at);

-- ============================================
-- Verification queries
-- ============================================

-- Verify columns added to worker_specialization
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'worker_specialization'
AND column_name IN ('specialization_title', 'base_hourly_rate', 'base_fixed_rate', 'premium_multiplier');

-- Verify columns added to gig_worker
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'gig_worker'
AND column_name IN ('specialized_rate_used', 'specialization_id');

-- Verify columns added to application
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'application'
AND column_name IN ('use_specialized_rate', 'specialization_id');

COMMIT;
