-- PostgreSQL Migration for Stripe Customer ID
-- Execute these queries in your PostgreSQL database to fix the missing stripe_customer_id column

-- 1. Add stripe_customer_id column to user table
ALTER TABLE "user"
ADD COLUMN IF NOT EXISTS stripe_customer_id VARCHAR(100);

-- 2. Add comment to document the column
COMMENT ON COLUMN "user".stripe_customer_id IS 'Stripe customer ID (cus_xxx) for saved payment methods';

-- 3. Create index for faster lookups by Stripe customer ID
CREATE INDEX IF NOT EXISTS idx_user_stripe_customer_id ON "user"(stripe_customer_id);

-- 4. Ensure StripeWebhookLog table exists (if not already created)
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

-- 5. Create indexes for StripeWebhookLog table
CREATE INDEX IF NOT EXISTS idx_stripe_webhook_event_id ON stripe_webhook_log(event_id);
CREATE INDEX IF NOT EXISTS idx_stripe_webhook_event_type ON stripe_webhook_log(event_type);
CREATE INDEX IF NOT EXISTS idx_stripe_webhook_processed ON stripe_webhook_log(processed);
CREATE INDEX IF NOT EXISTS idx_stripe_webhook_created_at ON stripe_webhook_log(created_at DESC);

-- 6. Verify the changes
SELECT column_name, data_type, character_maximum_length, is_nullable
FROM information_schema.columns
WHERE table_name = 'user' AND column_name = 'stripe_customer_id';

-- 7. Verify StripeWebhookLog table
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'stripe_webhook_log'
ORDER BY ordinal_position;

-- Expected output for user.stripe_customer_id:
-- column_name         | data_type      | character_maximum_length | is_nullable
-- stripe_customer_id  | character varying | 100                   | YES

-- Notes:
-- - stripe_customer_id stores Stripe customer IDs in format: cus_xxxxxxxxxxxxx
-- - This field is used to link users to their Stripe customer records
-- - Allows for saved payment methods and recurring payments
-- - The column is nullable as not all users will have Stripe customers
