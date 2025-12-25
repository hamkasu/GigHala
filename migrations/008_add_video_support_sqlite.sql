-- Migration: Add video support to gigs (SQLite)
-- Description: Add video_filename column to gig table for storing reference videos (max 15 seconds)
-- Date: 2025-12-25

-- Add video_filename column to gig table
ALTER TABLE gig ADD COLUMN video_filename VARCHAR(255);
