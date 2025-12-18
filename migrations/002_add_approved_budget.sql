-- Migration: Add Approved Budget Field
-- Description: Adds approved_budget column to gig table to store actual client-approved budget
-- Date: 2025-12-18
-- This migration is idempotent and safe to run multiple times

-- ============================================================================
-- POSTGRESQL VERSION
-- ============================================================================
-- Run this section if using PostgreSQL

-- Add approved_budget column to gig table (PostgreSQL)
DO $$
BEGIN
    -- Add approved_budget if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='gig' AND column_name='approved_budget') THEN
        ALTER TABLE gig ADD COLUMN approved_budget FLOAT;
    END IF;
END $$;

-- Create index for approved_budget for faster queries
CREATE INDEX IF NOT EXISTS idx_gig_approved_budget ON gig(approved_budget);

-- Optionally, migrate existing budget data (using average of budget_min and budget_max)
-- Uncomment if you want to populate approved_budget for existing gigs:
-- UPDATE gig
-- SET approved_budget = (budget_min + budget_max) / 2
-- WHERE approved_budget IS NULL;
