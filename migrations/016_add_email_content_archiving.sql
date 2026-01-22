-- Migration: Add Email Content Archiving
-- Description: Add columns to store complete email content and recipient details for compliance
-- Date: 2026-01-22

-- Add new columns to email_send_log table for complete email archiving
ALTER TABLE email_send_log
ADD COLUMN IF NOT EXISTS html_content TEXT,
ADD COLUMN IF NOT EXISTS text_content TEXT,
ADD COLUMN IF NOT EXISTS recipient_emails TEXT,
ADD COLUMN IF NOT EXISTS recipient_user_id INTEGER REFERENCES "user"(id);

-- Add index for recipient user queries
CREATE INDEX IF NOT EXISTS idx_email_send_log_recipient_user_id ON email_send_log(recipient_user_id);

-- Add comments for documentation
COMMENT ON COLUMN email_send_log.html_content IS 'HTML content of the email for archival purposes';
COMMENT ON COLUMN email_send_log.text_content IS 'Plain text content of the email for archival purposes';
COMMENT ON COLUMN email_send_log.recipient_emails IS 'JSON array of all recipient email addresses (successful and failed)';
COMMENT ON COLUMN email_send_log.recipient_user_id IS 'User ID of recipient for single-recipient transactional emails';
