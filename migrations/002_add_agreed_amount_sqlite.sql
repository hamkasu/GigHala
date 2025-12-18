-- GigHala Database Migration: Add agreed_amount column to gig table (SQLite version)
-- This migration adds the missing agreed_amount column that tracks the
-- agreed payment amount when a freelancer is assigned to a gig

-- ============================================
-- ADD AGREED_AMOUNT COLUMN TO GIG TABLE
-- ============================================

-- SQLite doesn't have IF NOT EXISTS for ALTER TABLE ADD COLUMN
-- We'll use a safer approach by checking if the column exists first
-- If this fails, the column already exists which is fine

-- Add agreed_amount column
-- Note: SQLite will fail if column already exists, but that's expected
ALTER TABLE gig ADD COLUMN agreed_amount REAL;

-- Create index on agreed_amount for better query performance
CREATE INDEX IF NOT EXISTS idx_gig_agreed_amount ON gig(agreed_amount)
WHERE agreed_amount IS NOT NULL;

-- ============================================
-- MIGRATION COMPLETE
-- ============================================
-- The gig table now has the agreed_amount column to track
-- the negotiated payment amount between client and freelancer
