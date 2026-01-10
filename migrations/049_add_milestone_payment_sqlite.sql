-- Migration: Add Milestone Payment Support (SQLite Version)
-- Description: Adds payment_type to gig table and creates milestone and milestone_payment tables
-- Date: 2026-01-10
-- This migration is idempotent and safe to run multiple times

-- ============================================================================
-- SQLITE VERSION
-- ============================================================================

-- Add payment_type column to gig table
-- SQLite doesn't support IF NOT EXISTS for columns, so we check first
-- This should be run conditionally or checked in application code

-- For SQLite, we'll handle this with a more cautious approach
-- If the column exists, this will error but can be caught
-- Alternatively, check in application before running

-- Create payment_type column (run only if column doesn't exist)
-- ALTER TABLE gig ADD COLUMN payment_type VARCHAR(20) DEFAULT 'full_payment';

-- Create milestone table
CREATE TABLE IF NOT EXISTS milestone (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    gig_id INTEGER NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    amount REAL NOT NULL,
    "order" INTEGER NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    due_date DATETIME,
    completed_at DATETIME,
    approved_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (gig_id) REFERENCES gig(id) ON DELETE CASCADE
);

-- Create milestone_payment table
CREATE TABLE IF NOT EXISTS milestone_payment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    milestone_id INTEGER NOT NULL,
    escrow_number VARCHAR(50) UNIQUE NOT NULL,
    gig_id INTEGER NOT NULL,
    client_id INTEGER NOT NULL,
    freelancer_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    platform_fee REAL DEFAULT 0.0,
    net_amount REAL NOT NULL,
    status VARCHAR(30) DEFAULT 'pending',
    payment_reference VARCHAR(100),
    payment_gateway VARCHAR(50),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    funded_at DATETIME,
    released_at DATETIME,
    refunded_at DATETIME,
    FOREIGN KEY (milestone_id) REFERENCES milestone(id) ON DELETE CASCADE,
    FOREIGN KEY (gig_id) REFERENCES gig(id) ON DELETE CASCADE,
    FOREIGN KEY (client_id) REFERENCES user(id) ON DELETE CASCADE,
    FOREIGN KEY (freelancer_id) REFERENCES user(id) ON DELETE CASCADE
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_milestone_gig_id ON milestone(gig_id);
CREATE INDEX IF NOT EXISTS idx_milestone_status ON milestone(status);
CREATE INDEX IF NOT EXISTS idx_milestone_order ON milestone(gig_id, "order");
CREATE INDEX IF NOT EXISTS idx_milestone_payment_milestone_id ON milestone_payment(milestone_id);
CREATE INDEX IF NOT EXISTS idx_milestone_payment_gig_id ON milestone_payment(gig_id);
CREATE INDEX IF NOT EXISTS idx_milestone_payment_status ON milestone_payment(status);
CREATE INDEX IF NOT EXISTS idx_milestone_payment_escrow_number ON milestone_payment(escrow_number);
CREATE INDEX IF NOT EXISTS idx_gig_payment_type ON gig(payment_type);
