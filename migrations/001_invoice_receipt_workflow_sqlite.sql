-- Migration: Invoice and Receipt Workflow (SQLite Version)
-- Description: Ensures all tables and columns exist for invoice/receipt workflow
-- Date: 2025-12-18
-- This migration is for SQLite databases
-- Note: SQLite doesn't support adding columns with constraints easily,
--       so this assumes tables are created via Flask-SQLAlchemy models

-- ============================================================================
-- SQLITE VERSION
-- ============================================================================

-- 1. Create Invoice table if not exists
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

-- 2. Create Receipt table if not exists
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

-- 3. Create Notification table if not exists
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

-- 4. Create indexes for better query performance (SQLite)
CREATE INDEX IF NOT EXISTS idx_invoice_gig_id ON invoice(gig_id);
CREATE INDEX IF NOT EXISTS idx_invoice_client_id ON invoice(client_id);
CREATE INDEX IF NOT EXISTS idx_invoice_freelancer_id ON invoice(freelancer_id);
CREATE INDEX IF NOT EXISTS idx_invoice_status ON invoice(status);
CREATE INDEX IF NOT EXISTS idx_invoice_created_at ON invoice(created_at);
CREATE INDEX IF NOT EXISTS idx_invoice_number ON invoice(invoice_number);

CREATE INDEX IF NOT EXISTS idx_receipt_gig_id ON receipt(gig_id);
CREATE INDEX IF NOT EXISTS idx_receipt_user_id ON receipt(user_id);
CREATE INDEX IF NOT EXISTS idx_receipt_invoice_id ON receipt(invoice_id);
CREATE INDEX IF NOT EXISTS idx_receipt_escrow_id ON receipt(escrow_id);
CREATE INDEX IF NOT EXISTS idx_receipt_type ON receipt(receipt_type);
CREATE INDEX IF NOT EXISTS idx_receipt_created_at ON receipt(created_at);
CREATE INDEX IF NOT EXISTS idx_receipt_number ON receipt(receipt_number);

CREATE INDEX IF NOT EXISTS idx_notification_user_id ON notification(user_id);
CREATE INDEX IF NOT EXISTS idx_notification_type ON notification(notification_type);
CREATE INDEX IF NOT EXISTS idx_notification_is_read ON notification(is_read);
CREATE INDEX IF NOT EXISTS idx_notification_related_id ON notification(related_id);
CREATE INDEX IF NOT EXISTS idx_notification_created_at ON notification(created_at);

-- SQLite doesn't support ALTER TABLE ADD COLUMN IF NOT EXISTS directly
-- If you need to add missing columns to existing tables, use this pattern:
--
-- PRAGMA table_info(invoice);  -- Check existing columns
-- ALTER TABLE invoice ADD COLUMN new_column_name TYPE DEFAULT value;
--
-- Or use Flask-SQLAlchemy migrations (Alembic) for safer schema changes
