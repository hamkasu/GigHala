-- =====================================================
-- GigHala Billing System Setup - SQL Migration Script
-- =====================================================
-- This script sets up the complete billing system including:
-- - Wallets for user balances
-- - Invoices for completed gigs
-- - Payout requests for freelancers
-- - Payment history tracking
-- =====================================================

-- 1. CREATE WALLET TABLE
-- Tracks user wallet balances and holds
CREATE TABLE IF NOT EXISTS wallet (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    balance DECIMAL(10, 2) DEFAULT 0.00 NOT NULL,
    held_balance DECIMAL(10, 2) DEFAULT 0.00 NOT NULL,
    total_earned DECIMAL(10, 2) DEFAULT 0.00 NOT NULL,
    total_spent DECIMAL(10, 2) DEFAULT 0.00 NOT NULL,
    currency VARCHAR(3) DEFAULT 'MYR' NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id)
);

-- 2. CREATE INVOICE TABLE
-- Generates invoices for completed transactions
CREATE TABLE IF NOT EXISTS invoice (
    id SERIAL PRIMARY KEY,
    invoice_number VARCHAR(50) UNIQUE NOT NULL,
    transaction_id INTEGER REFERENCES "transaction"(id) ON DELETE SET NULL,
    gig_id INTEGER NOT NULL REFERENCES gig(id) ON DELETE CASCADE,
    client_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    freelancer_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    amount DECIMAL(10, 2) NOT NULL,
    platform_fee DECIMAL(10, 2) DEFAULT 0.00,
    tax_amount DECIMAL(10, 2) DEFAULT 0.00,
    total_amount DECIMAL(10, 2) NOT NULL,
    status VARCHAR(20) DEFAULT 'draft' CHECK (status IN ('draft', 'issued', 'paid', 'cancelled', 'refunded')),
    payment_method VARCHAR(50),
    payment_reference VARCHAR(100),
    due_date TIMESTAMP,
    paid_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT
);

-- 3. CREATE PAYOUT TABLE
-- Handles freelancer payout requests
CREATE TABLE IF NOT EXISTS payout (
    id SERIAL PRIMARY KEY,
    payout_number VARCHAR(50) UNIQUE NOT NULL,
    freelancer_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    amount DECIMAL(10, 2) NOT NULL,
    fee DECIMAL(10, 2) DEFAULT 0.00,
    net_amount DECIMAL(10, 2) NOT NULL,
    payment_method VARCHAR(50) NOT NULL CHECK (payment_method IN ('bank_transfer', 'fpx', 'touch_n_go', 'grab_pay', 'boost')),
    account_number VARCHAR(100),
    account_name VARCHAR(200),
    bank_name VARCHAR(100),
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'cancelled')),
    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    completed_at TIMESTAMP,
    failure_reason TEXT,
    admin_notes TEXT
);

-- 4. CREATE PAYMENT_HISTORY TABLE
-- Comprehensive payment event tracking
CREATE TABLE IF NOT EXISTS payment_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    transaction_id INTEGER REFERENCES "transaction"(id) ON DELETE SET NULL,
    invoice_id INTEGER REFERENCES invoice(id) ON DELETE SET NULL,
    payout_id INTEGER REFERENCES payout(id) ON DELETE SET NULL,
    type VARCHAR(30) NOT NULL CHECK (type IN ('deposit', 'withdrawal', 'payment', 'refund', 'commission', 'payout', 'hold', 'release')),
    amount DECIMAL(10, 2) NOT NULL,
    balance_before DECIMAL(10, 2) NOT NULL,
    balance_after DECIMAL(10, 2) NOT NULL,
    description TEXT,
    reference_number VARCHAR(100),
    payment_gateway VARCHAR(50),
    gateway_response TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. ADD INDEXES FOR PERFORMANCE
CREATE INDEX IF NOT EXISTS idx_wallet_user_id ON wallet(user_id);
CREATE INDEX IF NOT EXISTS idx_invoice_client_id ON invoice(client_id);
CREATE INDEX IF NOT EXISTS idx_invoice_freelancer_id ON invoice(freelancer_id);
CREATE INDEX IF NOT EXISTS idx_invoice_transaction_id ON invoice(transaction_id);
CREATE INDEX IF NOT EXISTS idx_invoice_status ON invoice(status);
CREATE INDEX IF NOT EXISTS idx_invoice_created_at ON invoice(created_at);
CREATE INDEX IF NOT EXISTS idx_payout_freelancer_id ON payout(freelancer_id);
CREATE INDEX IF NOT EXISTS idx_payout_status ON payout(status);
CREATE INDEX IF NOT EXISTS idx_payout_requested_at ON payout(requested_at);
CREATE INDEX IF NOT EXISTS idx_payment_history_user_id ON payment_history(user_id);
CREATE INDEX IF NOT EXISTS idx_payment_history_type ON payment_history(type);
CREATE INDEX IF NOT EXISTS idx_payment_history_created_at ON payment_history(created_at);

-- 6. CREATE WALLET FOR EXISTING USERS
-- Initialize wallets for all existing users
INSERT INTO wallet (user_id, balance, held_balance, total_earned, total_spent, currency)
SELECT
    u.id,
    COALESCE(u.total_earnings, 0.00),
    0.00,
    COALESCE(u.total_earnings, 0.00),
    0.00,
    'MYR'
FROM "user" u
WHERE NOT EXISTS (SELECT 1 FROM wallet w WHERE w.user_id = u.id)
ON CONFLICT (user_id) DO NOTHING;

-- 7. CREATE FUNCTION TO AUTO-UPDATE WALLET TIMESTAMP
CREATE OR REPLACE FUNCTION update_wallet_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 8. CREATE TRIGGER FOR WALLET UPDATES
DROP TRIGGER IF EXISTS wallet_update_timestamp ON wallet;
CREATE TRIGGER wallet_update_timestamp
    BEFORE UPDATE ON wallet
    FOR EACH ROW
    EXECUTE FUNCTION update_wallet_timestamp();

-- 9. CREATE FUNCTION TO AUTO-UPDATE INVOICE TIMESTAMP
CREATE OR REPLACE FUNCTION update_invoice_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 10. CREATE TRIGGER FOR INVOICE UPDATES
DROP TRIGGER IF EXISTS invoice_update_timestamp ON invoice;
CREATE TRIGGER invoice_update_timestamp
    BEFORE UPDATE ON invoice
    FOR EACH ROW
    EXECUTE FUNCTION update_invoice_timestamp();

-- 11. CREATE VIEW FOR USER BILLING SUMMARY
CREATE OR REPLACE VIEW user_billing_summary AS
SELECT
    u.id as user_id,
    u.username,
    u.email,
    w.balance as wallet_balance,
    w.held_balance,
    w.total_earned,
    w.total_spent,
    COUNT(DISTINCT CASE WHEN t.status = 'completed' THEN t.id END) as completed_transactions,
    COUNT(DISTINCT CASE WHEN i.status = 'paid' THEN i.id END) as paid_invoices,
    COUNT(DISTINCT CASE WHEN p.status = 'completed' THEN p.id END) as completed_payouts,
    COALESCE(SUM(CASE WHEN t.status = 'pending' THEN t.amount END), 0) as pending_payments
FROM "user" u
LEFT JOIN wallet w ON u.id = w.user_id
LEFT JOIN "transaction" t ON u.id = t.client_id OR u.id = t.freelancer_id
LEFT JOIN invoice i ON u.id = i.client_id OR u.id = i.freelancer_id
LEFT JOIN payout p ON u.id = p.freelancer_id
GROUP BY u.id, u.username, u.email, w.balance, w.held_balance, w.total_earned, w.total_spent;

-- =====================================================
-- VERIFICATION QUERIES
-- Run these after migration to verify setup
-- =====================================================

-- Check if all tables were created
SELECT 'wallet' as table_name, COUNT(*) as row_count FROM wallet
UNION ALL
SELECT 'invoice', COUNT(*) FROM invoice
UNION ALL
SELECT 'payout', COUNT(*) FROM payout
UNION ALL
SELECT 'payment_history', COUNT(*) FROM payment_history;

-- Check if all users have wallets
SELECT
    COUNT(u.id) as total_users,
    COUNT(w.id) as users_with_wallets,
    COUNT(u.id) - COUNT(w.id) as users_without_wallets
FROM "user" u
LEFT JOIN wallet w ON u.id = w.user_id;

-- =====================================================
-- END OF BILLING SYSTEM SETUP
-- =====================================================
