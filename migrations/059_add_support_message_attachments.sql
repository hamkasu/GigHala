-- Migration 059: Add attachment fields to support_ticket_message table
-- Allows file attachments in support ticket conversations

ALTER TABLE support_ticket_message
    ADD COLUMN IF NOT EXISTS attachment_url VARCHAR(500),
    ADD COLUMN IF NOT EXISTS attachment_filename VARCHAR(255),
    ADD COLUMN IF NOT EXISTS attachment_type VARCHAR(20);
