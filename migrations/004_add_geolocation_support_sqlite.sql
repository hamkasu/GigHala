-- Database Migration: Add Geolocation Support (SQLite)
-- Date: 2025-12-19
-- Description: Adds latitude and longitude fields to User and Gig tables for location-based features

-- Add geolocation fields to user table
ALTER TABLE user ADD COLUMN latitude REAL;
ALTER TABLE user ADD COLUMN longitude REAL;

-- Add geolocation fields to gig table
ALTER TABLE gig ADD COLUMN latitude REAL;
ALTER TABLE gig ADD COLUMN longitude REAL;

-- Create indexes for faster geolocation queries
CREATE INDEX IF NOT EXISTS idx_user_location ON user(latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_gig_location ON gig(latitude, longitude);
