-- Migration: Add Email Send Log Table
-- Description: Add table to track all email sends for auditing and debugging
-- Date: 2026-01-01

-- Create email_send_log table
CREATE TABLE IF NOT EXISTS email_send_log (
    id SERIAL PRIMARY KEY,
    email_type VARCHAR(50) NOT NULL,
    subject VARCHAR(500),
    sender_user_id INTEGER REFERENCES "user"(id),
    recipient_count INTEGER DEFAULT 0,
    successful_count INTEGER DEFAULT 0,
    failed_count INTEGER DEFAULT 0,
    recipient_type VARCHAR(50),
    sent_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    brevo_message_ids TEXT,
    failed_recipients TEXT
);

-- Add indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_email_send_log_email_type ON email_send_log(email_type);
CREATE INDEX IF NOT EXISTS idx_email_send_log_sent_at ON email_send_log(sent_at DESC);
CREATE INDEX IF NOT EXISTS idx_email_send_log_success ON email_send_log(success);
CREATE INDEX IF NOT EXISTS idx_email_send_log_sender_user_id ON email_send_log(sender_user_id);

-- Add comments for documentation
COMMENT ON TABLE email_send_log IS 'Tracks all email sends for auditing and debugging purposes';
COMMENT ON COLUMN email_send_log.email_type IS 'Type of email: admin_bulk, admin_single, digest, transactional';
COMMENT ON COLUMN email_send_log.subject IS 'Email subject line';
COMMENT ON COLUMN email_send_log.sender_user_id IS 'User ID of admin who sent the email (if applicable)';
COMMENT ON COLUMN email_send_log.recipient_count IS 'Total number of intended recipients';
COMMENT ON COLUMN email_send_log.successful_count IS 'Number of successfully sent emails';
COMMENT ON COLUMN email_send_log.failed_count IS 'Number of failed email sends';
COMMENT ON COLUMN email_send_log.recipient_type IS 'Type of recipients: all, freelancers, clients, selected';
COMMENT ON COLUMN email_send_log.sent_at IS 'When the email send operation started';
COMMENT ON COLUMN email_send_log.success IS 'Whether the overall send operation succeeded';
COMMENT ON COLUMN email_send_log.error_message IS 'Error message if send failed';
COMMENT ON COLUMN email_send_log.brevo_message_ids IS 'JSON array of Brevo message IDs for tracking';
COMMENT ON COLUMN email_send_log.failed_recipients IS 'JSON array of email addresses that failed';
