-- Migration: Add Email Content Archiving (SQLite)
-- Description: Add columns to store complete email content and recipient details for compliance
-- Date: 2026-01-22

-- Add new columns to email_send_log table for complete email archiving
ALTER TABLE email_send_log ADD COLUMN html_content TEXT;
ALTER TABLE email_send_log ADD COLUMN text_content TEXT;
ALTER TABLE email_send_log ADD COLUMN recipient_emails TEXT;
ALTER TABLE email_send_log ADD COLUMN recipient_user_id INTEGER REFERENCES user(id);

-- Add index for recipient user queries
CREATE INDEX IF NOT EXISTS idx_email_send_log_recipient_user_id ON email_send_log(recipient_user_id);
