-- ============================================================================
-- MANUAL MIGRATION FOR POSTGRESQL
-- ============================================================================
-- Copy and paste these queries into your PostgreSQL client (psql, pgAdmin, etc.)
-- Execute them one by one or all at once
-- Safe to run multiple times (idempotent)

-- ============================================================================
-- STEP 1: CREATE INVOICE TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS invoice (
    id SERIAL PRIMARY KEY,
    invoice_number VARCHAR(50) UNIQUE NOT NULL,
    transaction_id INTEGER REFERENCES transaction(id),
    gig_id INTEGER NOT NULL REFERENCES gig(id),
    client_id INTEGER NOT NULL REFERENCES "user"(id),
    freelancer_id INTEGER NOT NULL REFERENCES "user"(id),
    amount FLOAT NOT NULL,
    platform_fee FLOAT DEFAULT 0.0,
    tax_amount FLOAT DEFAULT 0.0,
    total_amount FLOAT NOT NULL,
    status VARCHAR(20) DEFAULT 'draft',
    payment_method VARCHAR(50),
    payment_reference VARCHAR(100),
    due_date TIMESTAMP,
    paid_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT
);

-- ============================================================================
-- STEP 2: ADD MISSING COLUMNS TO INVOICE TABLE (if table already exists)
-- ============================================================================

-- Add invoice_number column
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='invoice' AND column_name='invoice_number'
    ) THEN
        ALTER TABLE invoice ADD COLUMN invoice_number VARCHAR(50) UNIQUE;
    END IF;
END $$;

-- Add due_date column
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='invoice' AND column_name='due_date'
    ) THEN
        ALTER TABLE invoice ADD COLUMN due_date TIMESTAMP;
    END IF;
END $$;

-- Add paid_at column
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='invoice' AND column_name='paid_at'
    ) THEN
        ALTER TABLE invoice ADD COLUMN paid_at TIMESTAMP;
    END IF;
END $$;

-- Add payment_reference column
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='invoice' AND column_name='payment_reference'
    ) THEN
        ALTER TABLE invoice ADD COLUMN payment_reference VARCHAR(100);
    END IF;
END $$;

-- Add notes column
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='invoice' AND column_name='notes'
    ) THEN
        ALTER TABLE invoice ADD COLUMN notes TEXT;
    END IF;
END $$;

-- ============================================================================
-- STEP 3: CREATE RECEIPT TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS receipt (
    id SERIAL PRIMARY KEY,
    receipt_number VARCHAR(50) UNIQUE NOT NULL,
    receipt_type VARCHAR(30) NOT NULL,
    user_id INTEGER NOT NULL REFERENCES "user"(id),
    gig_id INTEGER REFERENCES gig(id),
    escrow_id INTEGER REFERENCES escrow(id),
    invoice_id INTEGER REFERENCES invoice(id),
    transaction_id INTEGER REFERENCES transaction(id),
    amount FLOAT NOT NULL,
    platform_fee FLOAT DEFAULT 0.0,
    total_amount FLOAT NOT NULL,
    payment_method VARCHAR(50),
    payment_reference VARCHAR(100),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- STEP 4: ADD MISSING COLUMNS TO RECEIPT TABLE (if table already exists)
-- ============================================================================

-- Add receipt_number column
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='receipt' AND column_name='receipt_number'
    ) THEN
        ALTER TABLE receipt ADD COLUMN receipt_number VARCHAR(50) UNIQUE;
    END IF;
END $$;

-- Add receipt_type column
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='receipt' AND column_name='receipt_type'
    ) THEN
        ALTER TABLE receipt ADD COLUMN receipt_type VARCHAR(30) NOT NULL DEFAULT 'payment';
    END IF;
END $$;

-- Add invoice_id column
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='receipt' AND column_name='invoice_id'
    ) THEN
        ALTER TABLE receipt ADD COLUMN invoice_id INTEGER REFERENCES invoice(id);
    END IF;
END $$;

-- Add description column
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='receipt' AND column_name='description'
    ) THEN
        ALTER TABLE receipt ADD COLUMN description TEXT;
    END IF;
END $$;

-- ============================================================================
-- STEP 5: CREATE NOTIFICATION TABLE (if it doesn't exist)
-- ============================================================================

CREATE TABLE IF NOT EXISTS notification (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES "user"(id),
    notification_type VARCHAR(50) NOT NULL,
    title VARCHAR(200) NOT NULL,
    message TEXT,
    link VARCHAR(500),
    related_id INTEGER,
    is_read BOOLEAN DEFAULT FALSE,
    is_push_sent BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    read_at TIMESTAMP
);

-- ============================================================================
-- STEP 6: ADD MISSING COLUMNS TO NOTIFICATION TABLE (if table already exists)
-- ============================================================================

-- Add related_id column
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='notification' AND column_name='related_id'
    ) THEN
        ALTER TABLE notification ADD COLUMN related_id INTEGER;
    END IF;
END $$;

-- Add link column
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='notification' AND column_name='link'
    ) THEN
        ALTER TABLE notification ADD COLUMN link VARCHAR(500);
    END IF;
END $$;

-- ============================================================================
-- STEP 7: CREATE INDEXES FOR PERFORMANCE
-- ============================================================================

-- Invoice indexes
CREATE INDEX IF NOT EXISTS idx_invoice_gig_id ON invoice(gig_id);
CREATE INDEX IF NOT EXISTS idx_invoice_client_id ON invoice(client_id);
CREATE INDEX IF NOT EXISTS idx_invoice_freelancer_id ON invoice(freelancer_id);
CREATE INDEX IF NOT EXISTS idx_invoice_status ON invoice(status);
CREATE INDEX IF NOT EXISTS idx_invoice_created_at ON invoice(created_at);
CREATE INDEX IF NOT EXISTS idx_invoice_number ON invoice(invoice_number);

-- Receipt indexes
CREATE INDEX IF NOT EXISTS idx_receipt_gig_id ON receipt(gig_id);
CREATE INDEX IF NOT EXISTS idx_receipt_user_id ON receipt(user_id);
CREATE INDEX IF NOT EXISTS idx_receipt_invoice_id ON receipt(invoice_id);
CREATE INDEX IF NOT EXISTS idx_receipt_escrow_id ON receipt(escrow_id);
CREATE INDEX IF NOT EXISTS idx_receipt_type ON receipt(receipt_type);
CREATE INDEX IF NOT EXISTS idx_receipt_created_at ON receipt(created_at);
CREATE INDEX IF NOT EXISTS idx_receipt_number ON receipt(receipt_number);

-- Notification indexes
CREATE INDEX IF NOT EXISTS idx_notification_user_id ON notification(user_id);
CREATE INDEX IF NOT EXISTS idx_notification_type ON notification(notification_type);
CREATE INDEX IF NOT EXISTS idx_notification_is_read ON notification(is_read);
CREATE INDEX IF NOT EXISTS idx_notification_related_id ON notification(related_id);
CREATE INDEX IF NOT EXISTS idx_notification_created_at ON notification(created_at);

-- ============================================================================
-- STEP 8: ADD TABLE COMMENTS (Optional - for documentation)
-- ============================================================================

COMMENT ON TABLE invoice IS 'Stores invoices issued to clients for completed gigs';
COMMENT ON TABLE receipt IS 'Stores payment receipts for escrow funding and gig payments';
COMMENT ON TABLE notification IS 'Stores user notifications for various events';

COMMENT ON COLUMN invoice.status IS 'Invoice status: draft, issued, paid, cancelled, refunded';
COMMENT ON COLUMN invoice.due_date IS 'Payment due date (typically 7 days from issue)';
COMMENT ON COLUMN invoice.paid_at IS 'Timestamp when invoice was marked as paid';

COMMENT ON COLUMN receipt.receipt_type IS 'Receipt type: escrow_funding, payment, refund, payout';
COMMENT ON COLUMN receipt.invoice_id IS 'Links receipt to the invoice it settles';

COMMENT ON COLUMN notification.related_id IS 'ID of related entity (gig, invoice, receipt, etc.)';
COMMENT ON COLUMN notification.link IS 'Deep link to the relevant page in the app';

-- ============================================================================
-- MIGRATION COMPLETE!
-- ============================================================================
-- Run the verification queries in VERIFY.sql to confirm everything worked
