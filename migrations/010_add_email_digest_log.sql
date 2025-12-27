-- Migration: Add Email Digest Log Table
-- Description: Add table to track scheduled email digests (new gigs, etc.)
-- Date: 2025-12-27

-- Create email_digest_log table
CREATE TABLE IF NOT EXISTS email_digest_log (
    id SERIAL PRIMARY KEY,
    digest_type VARCHAR(50) NOT NULL,
    sent_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    recipient_count INTEGER DEFAULT 0,
    gig_count INTEGER DEFAULT 0,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT
);

-- Add indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_email_digest_log_digest_type ON email_digest_log(digest_type);
CREATE INDEX IF NOT EXISTS idx_email_digest_log_sent_at ON email_digest_log(sent_at DESC);
CREATE INDEX IF NOT EXISTS idx_email_digest_log_success ON email_digest_log(success);

-- Add comments for documentation
COMMENT ON TABLE email_digest_log IS 'Tracks scheduled email digest sends (e.g., new gigs notifications)';
COMMENT ON COLUMN email_digest_log.digest_type IS 'Type of digest: new_gigs, weekly_summary, etc.';
COMMENT ON COLUMN email_digest_log.sent_at IS 'When the digest was sent';
COMMENT ON COLUMN email_digest_log.recipient_count IS 'Number of emails sent in this digest';
COMMENT ON COLUMN email_digest_log.gig_count IS 'Number of gigs included in the digest';
COMMENT ON COLUMN email_digest_log.success IS 'Whether the digest was sent successfully';
COMMENT ON COLUMN email_digest_log.error_message IS 'Error message if send failed';
