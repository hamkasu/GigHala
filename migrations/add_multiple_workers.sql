-- ============================================================================
-- SQL Migration: Add Multiple Workers Support for Gigs
-- ============================================================================
-- This migration adds support for gigs that require multiple workers.
-- Run these queries manually to update the database.
-- ============================================================================

-- ============================================================================
-- STEP 1: Add workers_needed column to gig table
-- ============================================================================

-- Add workers_needed column (defaults to 1 for backward compatibility)
ALTER TABLE gig ADD COLUMN workers_needed INTEGER DEFAULT 1;

-- Update existing gigs to have workers_needed = 1
UPDATE gig SET workers_needed = 1 WHERE workers_needed IS NULL;

-- ============================================================================
-- STEP 2: Create gig_worker table for tracking multiple workers per gig
-- ============================================================================

-- Create the gig_worker table
CREATE TABLE IF NOT EXISTS gig_worker (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    gig_id INTEGER NOT NULL,
    worker_id INTEGER NOT NULL,
    application_id INTEGER NOT NULL,
    agreed_amount FLOAT,
    status VARCHAR(20) DEFAULT 'active',  -- active, completed, withdrawn
    work_submitted BOOLEAN DEFAULT 0,
    work_submission_date DATETIME,
    completion_notes TEXT,
    assigned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME,
    FOREIGN KEY (gig_id) REFERENCES gig(id),
    FOREIGN KEY (worker_id) REFERENCES user(id),
    FOREIGN KEY (application_id) REFERENCES application(id),
    UNIQUE (gig_id, worker_id)
);

-- Create indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_gig_worker_gig_id ON gig_worker(gig_id);
CREATE INDEX IF NOT EXISTS idx_gig_worker_worker_id ON gig_worker(worker_id);
CREATE INDEX IF NOT EXISTS idx_gig_worker_status ON gig_worker(status);

-- ============================================================================
-- STEP 3: Migrate existing single-worker assignments to gig_worker table
-- ============================================================================
-- This ensures backward compatibility by creating GigWorker entries for
-- existing gigs that have a freelancer_id assigned.

INSERT INTO gig_worker (gig_id, worker_id, application_id, agreed_amount, status, assigned_at)
SELECT
    g.id as gig_id,
    g.freelancer_id as worker_id,
    a.id as application_id,
    COALESCE(g.agreed_amount, a.proposed_price, g.budget_min) as agreed_amount,
    CASE
        WHEN g.status = 'completed' THEN 'completed'
        WHEN g.status = 'cancelled' THEN 'withdrawn'
        ELSE 'active'
    END as status,
    g.created_at as assigned_at
FROM gig g
INNER JOIN application a ON a.gig_id = g.id AND a.freelancer_id = g.freelancer_id AND a.status = 'accepted'
WHERE g.freelancer_id IS NOT NULL
AND NOT EXISTS (
    SELECT 1 FROM gig_worker gw WHERE gw.gig_id = g.id AND gw.worker_id = g.freelancer_id
);

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Check if workers_needed column was added
-- SELECT name, type FROM pragma_table_info('gig') WHERE name = 'workers_needed';

-- Check if gig_worker table was created
-- SELECT name FROM sqlite_master WHERE type='table' AND name='gig_worker';

-- Count migrated records
-- SELECT COUNT(*) as migrated_workers FROM gig_worker;

-- View multi-worker gig stats
-- SELECT workers_needed, COUNT(*) as gig_count FROM gig GROUP BY workers_needed;

-- ============================================================================
-- ROLLBACK QUERIES (Use these if you need to undo the migration)
-- ============================================================================

-- WARNING: Only run these if you need to completely undo the migration
-- This will result in data loss!

-- DROP TABLE IF EXISTS gig_worker;
--
-- -- For SQLite, you cannot drop a column directly. You would need to:
-- -- 1. Create a new table without the column
-- -- 2. Copy data
-- -- 3. Drop old table
-- -- 4. Rename new table

-- ============================================================================
-- POSTGRESQL VERSION (if using PostgreSQL instead of SQLite)
-- ============================================================================

-- -- Add workers_needed column
-- ALTER TABLE gig ADD COLUMN IF NOT EXISTS workers_needed INTEGER DEFAULT 1;
--
-- -- Create gig_worker table
-- CREATE TABLE IF NOT EXISTS gig_worker (
--     id SERIAL PRIMARY KEY,
--     gig_id INTEGER NOT NULL REFERENCES gig(id),
--     worker_id INTEGER NOT NULL REFERENCES "user"(id),
--     application_id INTEGER NOT NULL REFERENCES application(id),
--     agreed_amount DECIMAL(10, 2),
--     status VARCHAR(20) DEFAULT 'active',
--     work_submitted BOOLEAN DEFAULT FALSE,
--     work_submission_date TIMESTAMP,
--     completion_notes TEXT,
--     assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
--     completed_at TIMESTAMP,
--     UNIQUE (gig_id, worker_id)
-- );
--
-- CREATE INDEX IF NOT EXISTS idx_gig_worker_gig_id ON gig_worker(gig_id);
-- CREATE INDEX IF NOT EXISTS idx_gig_worker_worker_id ON gig_worker(worker_id);
-- CREATE INDEX IF NOT EXISTS idx_gig_worker_status ON gig_worker(status);

-- ============================================================================
-- MYSQL VERSION (if using MySQL instead of SQLite)
-- ============================================================================

-- -- Add workers_needed column
-- ALTER TABLE gig ADD COLUMN workers_needed INT DEFAULT 1;
--
-- -- Create gig_worker table
-- CREATE TABLE IF NOT EXISTS gig_worker (
--     id INT AUTO_INCREMENT PRIMARY KEY,
--     gig_id INT NOT NULL,
--     worker_id INT NOT NULL,
--     application_id INT NOT NULL,
--     agreed_amount DECIMAL(10, 2),
--     status VARCHAR(20) DEFAULT 'active',
--     work_submitted TINYINT(1) DEFAULT 0,
--     work_submission_date DATETIME,
--     completion_notes TEXT,
--     assigned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
--     completed_at DATETIME,
--     FOREIGN KEY (gig_id) REFERENCES gig(id),
--     FOREIGN KEY (worker_id) REFERENCES user(id),
--     FOREIGN KEY (application_id) REFERENCES application(id),
--     UNIQUE KEY unique_worker_per_gig (gig_id, worker_id),
--     INDEX idx_gig_worker_gig_id (gig_id),
--     INDEX idx_gig_worker_worker_id (worker_id),
--     INDEX idx_gig_worker_status (status)
-- );
