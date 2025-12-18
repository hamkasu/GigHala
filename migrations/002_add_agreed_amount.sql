-- GigHala Database Migration: Add agreed_amount column to gig table
-- This migration adds the missing agreed_amount column that tracks the
-- agreed payment amount when a freelancer is assigned to a gig

-- ============================================
-- ADD AGREED_AMOUNT COLUMN TO GIG TABLE
-- ============================================

-- Check if the column exists before adding it
DO $$
BEGIN
    -- Add agreed_amount column if not exists
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'gig' AND column_name = 'agreed_amount') THEN
        ALTER TABLE gig ADD COLUMN agreed_amount NUMERIC(10, 2);
        RAISE NOTICE 'Column agreed_amount added to gig table';
    ELSE
        RAISE NOTICE 'Column agreed_amount already exists in gig table';
    END IF;
END $$;

-- Create index on agreed_amount for better query performance
CREATE INDEX IF NOT EXISTS idx_gig_agreed_amount ON gig(agreed_amount)
WHERE agreed_amount IS NOT NULL;

-- ============================================
-- MIGRATION COMPLETE
-- ============================================
-- The gig table now has the agreed_amount column to track
-- the negotiated payment amount between client and freelancer
