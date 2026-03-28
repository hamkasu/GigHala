-- ============================================================================
-- Migration 051: Multiple Jobs Per Worker with Individual Escrow
-- ============================================================================
-- Enables clients to assign unlimited separate jobs to the same worker,
-- each with its own independently managed escrow.
--
-- Changes:
--   1. Add escrow_id FK to gig_worker (links each worker slot to its escrow)
--   2. Add unique constraint on escrow(gig_id, freelancer_id) so each worker
--      in a gig has at most one escrow record
-- ============================================================================

-- ============================================================================
-- STEP 1: Add escrow_id column to gig_worker
-- ============================================================================

-- PostgreSQL
ALTER TABLE gig_worker ADD COLUMN IF NOT EXISTS escrow_id INTEGER REFERENCES escrow(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_gig_worker_escrow_id ON gig_worker(escrow_id);

-- ============================================================================
-- STEP 2: Ensure Escrow table has a unique constraint per (gig_id, freelancer_id)
-- This allows each worker on a multi-worker gig to have their own escrow row.
-- ============================================================================

-- Drop old single-column unique index on gig_id if it exists (legacy: one escrow per gig)
-- Only run this if such a constraint exists in your schema.
-- (The SQLAlchemy model did NOT define a unique constraint on gig_id alone,
--  so this may be a no-op. Verify before running.)
-- DROP INDEX IF EXISTS ix_escrow_gig_id;

-- Add the new composite unique constraint
ALTER TABLE escrow ADD CONSTRAINT unique_escrow_per_gig_worker UNIQUE (gig_id, freelancer_id);

-- ============================================================================
-- ROLLBACK
-- ============================================================================
-- ALTER TABLE gig_worker DROP COLUMN IF EXISTS escrow_id;
-- ALTER TABLE escrow DROP CONSTRAINT IF EXISTS unique_escrow_per_gig_worker;

-- ============================================================================
-- SQLite version (SQLite does not support ADD CONSTRAINT or ADD COLUMN with FK)
-- ============================================================================
-- For SQLite, rebuild the gig_worker table manually:
--
-- CREATE TABLE gig_worker_new (
--     id INTEGER PRIMARY KEY AUTOINCREMENT,
--     gig_id INTEGER NOT NULL,
--     worker_id INTEGER NOT NULL,
--     application_id INTEGER NOT NULL,
--     escrow_id INTEGER,
--     agreed_amount FLOAT,
--     status VARCHAR(20) DEFAULT 'active',
--     work_submitted BOOLEAN DEFAULT 0,
--     work_submission_date DATETIME,
--     completion_notes TEXT,
--     assigned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
--     completed_at DATETIME,
--     specialized_rate_used BOOLEAN DEFAULT 0,
--     specialization_id INTEGER,
--     FOREIGN KEY (gig_id) REFERENCES gig(id),
--     FOREIGN KEY (worker_id) REFERENCES "user"(id),
--     FOREIGN KEY (application_id) REFERENCES application(id),
--     FOREIGN KEY (escrow_id) REFERENCES escrow(id),
--     UNIQUE (gig_id, worker_id)
-- );
-- INSERT INTO gig_worker_new SELECT id, gig_id, worker_id, application_id,
--     NULL, agreed_amount, status, work_submitted, work_submission_date,
--     completion_notes, assigned_at, completed_at,
--     specialized_rate_used, specialization_id FROM gig_worker;
-- DROP TABLE gig_worker;
-- ALTER TABLE gig_worker_new RENAME TO gig_worker;
--
-- For escrow unique constraint in SQLite, rebuild escrow table similarly
-- and add UNIQUE (gig_id, freelancer_id) to the new table definition.
