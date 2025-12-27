-- Migration: Add Email Digest Log Table (SQLite)
-- Description: Add table to track scheduled email digests (new gigs, etc.)
-- Date: 2025-12-27

-- Create email_digest_log table
CREATE TABLE IF NOT EXISTS email_digest_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    digest_type TEXT NOT NULL,
    sent_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    recipient_count INTEGER DEFAULT 0,
    gig_count INTEGER DEFAULT 0,
    success INTEGER DEFAULT 1,  -- SQLite uses INTEGER for boolean (1=true, 0=false)
    error_message TEXT
);

-- Add indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_email_digest_log_digest_type ON email_digest_log(digest_type);
CREATE INDEX IF NOT EXISTS idx_email_digest_log_sent_at ON email_digest_log(sent_at DESC);
CREATE INDEX IF NOT EXISTS idx_email_digest_log_success ON email_digest_log(success);
