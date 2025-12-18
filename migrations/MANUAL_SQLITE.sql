-- ============================================================================
-- MANUAL MIGRATION FOR SQLITE
-- ============================================================================
-- Copy and paste these queries into your SQLite client
-- Execute them one by one or all at once
-- Safe to run multiple times (idempotent)

-- NOTE: SQLite has limitations with ALTER TABLE
-- If you get errors, use the Flask-SQLAlchemy method instead:
--   python3 -c "from app import app, db; db.create_all()"

-- ============================================================================
-- STEP 1: CREATE INVOICE TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS invoice (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_number VARCHAR(50) UNIQUE NOT NULL,
    transaction_id INTEGER REFERENCES transaction(id),
    gig_id INTEGER NOT NULL REFERENCES gig(id),
    client_id INTEGER NOT NULL REFERENCES user(id),
    freelancer_id INTEGER NOT NULL REFERENCES user(id),
    amount REAL NOT NULL,
    platform_fee REAL DEFAULT 0.0,
    tax_amount REAL DEFAULT 0.0,
    total_amount REAL NOT NULL,
    status VARCHAR(20) DEFAULT 'draft',
    payment_method VARCHAR(50),
    payment_reference VARCHAR(100),
    due_date DATETIME,
    paid_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    notes TEXT
);

-- ============================================================================
-- STEP 2: ADD MISSING COLUMNS TO INVOICE TABLE (if needed)
-- ============================================================================
-- SQLite doesn't support conditional ALTER TABLE, so these may fail if columns exist
-- That's OK - just ignore "duplicate column name" errors

-- Add invoice_number column (if missing)
-- ALTER TABLE invoice ADD COLUMN invoice_number VARCHAR(50);

-- Add due_date column (if missing)
-- ALTER TABLE invoice ADD COLUMN due_date DATETIME;

-- Add paid_at column (if missing)
-- ALTER TABLE invoice ADD COLUMN paid_at DATETIME;

-- Add payment_reference column (if missing)
-- ALTER TABLE invoice ADD COLUMN payment_reference VARCHAR(100);

-- Add notes column (if missing)
-- ALTER TABLE invoice ADD COLUMN notes TEXT;

-- NOTE: Uncomment the above lines ONE AT A TIME if you need to add missing columns
-- Skip any that already exist (you'll get an error but it's harmless)

-- ============================================================================
-- STEP 3: CREATE RECEIPT TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS receipt (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    receipt_number VARCHAR(50) UNIQUE NOT NULL,
    receipt_type VARCHAR(30) NOT NULL,
    user_id INTEGER NOT NULL REFERENCES user(id),
    gig_id INTEGER REFERENCES gig(id),
    escrow_id INTEGER REFERENCES escrow(id),
    invoice_id INTEGER REFERENCES invoice(id),
    transaction_id INTEGER REFERENCES transaction(id),
    amount REAL NOT NULL,
    platform_fee REAL DEFAULT 0.0,
    total_amount REAL NOT NULL,
    payment_method VARCHAR(50),
    payment_reference VARCHAR(100),
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- STEP 4: ADD MISSING COLUMNS TO RECEIPT TABLE (if needed)
-- ============================================================================
-- Uncomment these ONE AT A TIME if you need to add missing columns

-- Add receipt_number column (if missing)
-- ALTER TABLE receipt ADD COLUMN receipt_number VARCHAR(50);

-- Add receipt_type column (if missing)
-- ALTER TABLE receipt ADD COLUMN receipt_type VARCHAR(30) DEFAULT 'payment';

-- Add invoice_id column (if missing)
-- ALTER TABLE receipt ADD COLUMN invoice_id INTEGER REFERENCES invoice(id);

-- Add description column (if missing)
-- ALTER TABLE receipt ADD COLUMN description TEXT;

-- ============================================================================
-- STEP 5: CREATE NOTIFICATION TABLE (if it doesn't exist)
-- ============================================================================

CREATE TABLE IF NOT EXISTS notification (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES user(id),
    notification_type VARCHAR(50) NOT NULL,
    title VARCHAR(200) NOT NULL,
    message TEXT,
    link VARCHAR(500),
    related_id INTEGER,
    is_read BOOLEAN DEFAULT 0,
    is_push_sent BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    read_at DATETIME
);

-- ============================================================================
-- STEP 6: ADD MISSING COLUMNS TO NOTIFICATION TABLE (if needed)
-- ============================================================================
-- Uncomment these ONE AT A TIME if you need to add missing columns

-- Add related_id column (if missing)
-- ALTER TABLE notification ADD COLUMN related_id INTEGER;

-- Add link column (if missing)
-- ALTER TABLE notification ADD COLUMN link VARCHAR(500);

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
-- MIGRATION COMPLETE!
-- ============================================================================
-- Run the verification queries in VERIFY.sql to confirm everything worked
