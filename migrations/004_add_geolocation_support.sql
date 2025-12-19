-- Database Migration: Add Geolocation Support
-- Date: 2025-12-19
-- Description: Adds latitude and longitude fields to User and Gig tables for location-based features

-- Add geolocation fields to user table
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS latitude FLOAT;
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS longitude FLOAT;

-- Add geolocation fields to gig table
ALTER TABLE gig ADD COLUMN IF NOT EXISTS latitude FLOAT;
ALTER TABLE gig ADD COLUMN IF NOT EXISTS longitude FLOAT;

-- Create indexes for faster geolocation queries
CREATE INDEX IF NOT EXISTS idx_user_location ON "user"(latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_gig_location ON gig(latitude, longitude);

-- Comments
COMMENT ON COLUMN "user".latitude IS 'Geographic latitude for user location';
COMMENT ON COLUMN "user".longitude IS 'Geographic longitude for user location';
COMMENT ON COLUMN gig.latitude IS 'Geographic latitude for gig location';
COMMENT ON COLUMN gig.longitude IS 'Geographic longitude for gig location';
