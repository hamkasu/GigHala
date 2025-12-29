-- Migration: Add Stripe webhook logging table
-- Date: 2025-12-29
-- Description: Track all Stripe webhook events for debugging and auditing

CREATE TABLE IF NOT EXISTS stripe_webhook_log (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(100) UNIQUE NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    payload TEXT,
    processed BOOLEAN DEFAULT FALSE,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP
);

-- Create indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_webhook_log_event_id ON stripe_webhook_log(event_id);
CREATE INDEX IF NOT EXISTS idx_webhook_log_event_type ON stripe_webhook_log(event_type);
CREATE INDEX IF NOT EXISTS idx_webhook_log_processed ON stripe_webhook_log(processed);
CREATE INDEX IF NOT EXISTS idx_webhook_log_created_at ON stripe_webhook_log(created_at);
