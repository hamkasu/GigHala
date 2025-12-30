-- Migration 012: Add Content Moderation System (SQLite)
-- Description: Adds ContentModerationLog table for tracking image moderation results
-- Date: 2025-12-30
-- Database: SQLite

-- Create ContentModerationLog table
CREATE TABLE IF NOT EXISTS content_moderation_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
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
    ip_address VARCHAR(45),
    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_content_moderation_user_id ON content_moderation_log(user_id);
CREATE INDEX IF NOT EXISTS idx_content_moderation_image_type ON content_moderation_log(image_type);
CREATE INDEX IF NOT EXISTS idx_content_moderation_is_safe ON content_moderation_log(is_safe);
CREATE INDEX IF NOT EXISTS idx_content_moderation_created_at ON content_moderation_log(created_at);
