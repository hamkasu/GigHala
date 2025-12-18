-- Migration: Add Approved Budget Field (SQLite)
-- Description: Adds approved_budget column to gig table to store actual client-approved budget
-- Date: 2025-12-18
-- This migration is idempotent and safe to run multiple times

-- ============================================================================
-- SQLITE VERSION
-- ============================================================================

-- Add approved_budget column to gig table (SQLite)
-- SQLite doesn't support IF NOT EXISTS for ALTER TABLE, so this will fail silently if column exists
ALTER TABLE gig ADD COLUMN approved_budget REAL;

-- Create index for approved_budget for faster queries
CREATE INDEX IF NOT EXISTS idx_gig_approved_budget ON gig(approved_budget);

-- Optionally, migrate existing budget data (using average of budget_min and budget_max)
-- Uncomment if you want to populate approved_budget for existing gigs:
-- UPDATE gig
-- SET approved_budget = (budget_min + budget_max) / 2.0
-- WHERE approved_budget IS NULL;
