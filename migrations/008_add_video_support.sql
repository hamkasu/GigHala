-- Migration: Add video support to gigs
-- Description: Add video_filename column to gig table for storing reference videos (max 15 seconds)
-- Date: 2025-12-25

-- Add video_filename column to gig table
ALTER TABLE gig ADD COLUMN video_filename VARCHAR(255);

-- Add comment to document the column
COMMENT ON COLUMN gig.video_filename IS 'Reference video filename (max 15 seconds)';
