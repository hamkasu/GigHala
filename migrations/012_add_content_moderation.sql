-- Migration 012: Add Content Moderation System
-- Description: Adds ContentModerationLog table for tracking image moderation results
-- Date: 2025-12-30
-- Database: PostgreSQL

-- Create ContentModerationLog table
CREATE TABLE IF NOT EXISTS content_moderation_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    image_type VARCHAR(50) NOT NULL,
    image_path VARCHAR(500) NOT NULL,
    image_filename VARCHAR(255) NOT NULL,
    is_safe BOOLEAN NOT NULL,
    violations TEXT,
    adult_likelihood VARCHAR(20),
    violence_likelihood VARCHAR(20),
    racy_likelihood VARCHAR(20),
    medical_likelihood VARCHAR(20),
    spoof_likelihood VARCHAR(20),
    moderation_details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(45)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_content_moderation_user_id ON content_moderation_log(user_id);
CREATE INDEX IF NOT EXISTS idx_content_moderation_image_type ON content_moderation_log(image_type);
CREATE INDEX IF NOT EXISTS idx_content_moderation_is_safe ON content_moderation_log(is_safe);
CREATE INDEX IF NOT EXISTS idx_content_moderation_created_at ON content_moderation_log(created_at);

-- Add comments for documentation
COMMENT ON TABLE content_moderation_log IS 'Tracks content moderation results for all uploaded images';
COMMENT ON COLUMN content_moderation_log.user_id IS 'User who uploaded the image';
COMMENT ON COLUMN content_moderation_log.image_type IS 'Type of image: gig_photo, work_photo, portfolio, verification';
COMMENT ON COLUMN content_moderation_log.image_path IS 'Full file system path to the image';
COMMENT ON COLUMN content_moderation_log.image_filename IS 'Filename of the uploaded image';
COMMENT ON COLUMN content_moderation_log.is_safe IS 'Whether the image passed content moderation';
COMMENT ON COLUMN content_moderation_log.violations IS 'JSON array of violation types detected';
COMMENT ON COLUMN content_moderation_log.adult_likelihood IS 'Google Vision API adult content likelihood';
COMMENT ON COLUMN content_moderation_log.violence_likelihood IS 'Google Vision API violence likelihood';
COMMENT ON COLUMN content_moderation_log.racy_likelihood IS 'Google Vision API racy content likelihood';
COMMENT ON COLUMN content_moderation_log.medical_likelihood IS 'Google Vision API medical content likelihood';
COMMENT ON COLUMN content_moderation_log.spoof_likelihood IS 'Google Vision API spoof likelihood';
COMMENT ON COLUMN content_moderation_log.moderation_details IS 'Full JSON moderation details from the API';
COMMENT ON COLUMN content_moderation_log.created_at IS 'Timestamp when the moderation was performed';
COMMENT ON COLUMN content_moderation_log.ip_address IS 'IP address of the uploader';

-- Grant permissions (adjust as needed for your setup)
-- GRANT SELECT, INSERT ON content_moderation_log TO your_app_user;
-- GRANT USAGE, SELECT ON SEQUENCE content_moderation_log_id_seq TO your_app_user;
