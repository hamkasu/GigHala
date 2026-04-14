-- Migration 059 (SQLite): Add attachment fields to support_ticket_message table
-- SQLite does not support ADD COLUMN IF NOT EXISTS or multiple columns in one ALTER TABLE

ALTER TABLE support_ticket_message ADD COLUMN attachment_url VARCHAR(500);
ALTER TABLE support_ticket_message ADD COLUMN attachment_filename VARCHAR(255);
ALTER TABLE support_ticket_message ADD COLUMN attachment_type VARCHAR(20);
