-- Migration 050: Add Specialized Worker Rates (SQLite version)
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
--
-- Note: SQLite doesn't support IF NOT EXISTS for ALTER TABLE,
-- so these statements may fail if columns already exist - that's OK.

-- ============================================
-- 1. Add rate fields to worker_specialization
-- ============================================

-- Add specialization_title column (custom title like "Senior Quran Tutor")
ALTER TABLE worker_specialization ADD COLUMN specialization_title VARCHAR(100);

-- Add base_hourly_rate column (MYR per hour)
ALTER TABLE worker_specialization ADD COLUMN base_hourly_rate REAL;

-- Add base_fixed_rate column (MYR per fixed gig)
ALTER TABLE worker_specialization ADD COLUMN base_fixed_rate REAL;

-- Add premium_multiplier column (default 1.0, e.g., 1.2 = 20% premium)
ALTER TABLE worker_specialization ADD COLUMN premium_multiplier REAL DEFAULT 1.0;

-- ============================================
-- 2. Add specialized rate tracking to gig_worker
-- ============================================

-- Add specialized_rate_used flag for analytics
ALTER TABLE gig_worker ADD COLUMN specialized_rate_used INTEGER DEFAULT 0;

-- Add reference to the specialization used
ALTER TABLE gig_worker ADD COLUMN specialization_id INTEGER REFERENCES worker_specialization(id);

-- ============================================
-- 3. Add specialized rate reference to application
-- ============================================

-- Add flag for when worker uses specialized rate
ALTER TABLE application ADD COLUMN use_specialized_rate INTEGER DEFAULT 0;

-- Add reference to the specialization used in application
ALTER TABLE application ADD COLUMN specialization_id INTEGER REFERENCES worker_specialization(id);

-- ============================================
-- 4. Create indexes for efficient queries
-- ============================================

-- Index for finding workers by rate
CREATE INDEX IF NOT EXISTS idx_worker_spec_hourly_rate ON worker_specialization(base_hourly_rate);
CREATE INDEX IF NOT EXISTS idx_worker_spec_fixed_rate ON worker_specialization(base_fixed_rate);

-- Index for analytics on specialized rate usage
CREATE INDEX IF NOT EXISTS idx_gig_worker_specialized ON gig_worker(specialized_rate_used);

-- ============================================
-- 5. Add audit table for rate changes (PDPA compliance)
-- ============================================

CREATE TABLE IF NOT EXISTS worker_rate_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    specialization_id INTEGER REFERENCES worker_specialization(id),
    user_id INTEGER REFERENCES user(id),
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
