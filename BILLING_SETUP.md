# GigHala Billing System Setup Guide

## Quick Setup - Run These SQL Queries

To set up the complete billing system, run the SQL migration script on your Railway database:

### Option 1: Run the Complete Migration Script

Execute the entire migration script located at `migrations/setup_billing_system.sql` in your Railway PostgreSQL database.

You can do this via Railway's dashboard:
1. Go to your Railway project
2. Click on your PostgreSQL database
3. Go to "Query" tab
4. Copy and paste the contents of `migrations/setup_billing_system.sql`
5. Click "Execute"

### Option 2: Manual SQL Queries (Essential Only)

If you prefer to run queries manually, here are the essential commands:

```sql
-- 1. CREATE WALLET TABLE
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
    status VARCHAR(20) DEFAULT 'draft',
    payment_method VARCHAR(50),
    payment_reference VARCHAR(100),
    due_date TIMESTAMP,
    paid_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT
);

-- 3. CREATE PAYOUT TABLE
CREATE TABLE IF NOT EXISTS payout (
    id SERIAL PRIMARY KEY,
    payout_number VARCHAR(50) UNIQUE NOT NULL,
    freelancer_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    amount DECIMAL(10, 2) NOT NULL,
    fee DECIMAL(10, 2) DEFAULT 0.00,
    net_amount DECIMAL(10, 2) NOT NULL,
    payment_method VARCHAR(50) NOT NULL,
    account_number VARCHAR(100),
    account_name VARCHAR(200),
    bank_name VARCHAR(100),
    status VARCHAR(20) DEFAULT 'pending',
    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    completed_at TIMESTAMP,
    failure_reason TEXT,
    admin_notes TEXT
);

-- 4. CREATE PAYMENT_HISTORY TABLE
CREATE TABLE IF NOT EXISTS payment_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    transaction_id INTEGER REFERENCES "transaction"(id) ON DELETE SET NULL,
    invoice_id INTEGER REFERENCES invoice(id) ON DELETE SET NULL,
    payout_id INTEGER REFERENCES payout(id) ON DELETE SET NULL,
    type VARCHAR(30) NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    balance_before DECIMAL(10, 2) NOT NULL,
    balance_after DECIMAL(10, 2) NOT NULL,
    description TEXT,
    reference_number VARCHAR(100),
    payment_gateway VARCHAR(50),
    gateway_response TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. CREATE INDEXES FOR PERFORMANCE
CREATE INDEX IF NOT EXISTS idx_wallet_user_id ON wallet(user_id);
CREATE INDEX IF NOT EXISTS idx_invoice_client_id ON invoice(client_id);
CREATE INDEX IF NOT EXISTS idx_invoice_freelancer_id ON invoice(freelancer_id);
CREATE INDEX IF NOT EXISTS idx_payout_freelancer_id ON payout(freelancer_id);
CREATE INDEX IF NOT EXISTS idx_payment_history_user_id ON payment_history(user_id);

-- 6. INITIALIZE WALLETS FOR EXISTING USERS
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
```

## Verification

After running the migration, verify the setup with:

```sql
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
    COUNT(w.id) as users_with_wallets
FROM "user" u
LEFT JOIN wallet w ON u.id = w.user_id;
```

## New Features

### For Users:
- **Billing Dashboard**: Access at `/billing`
- **Wallet Management**: View balance, earnings, and spending
- **Transaction History**: Track all payments sent and received
- **Invoice Management**: View and manage invoices
- **Payout Requests**: Request withdrawals to bank or eWallet
- **Payment History**: Detailed payment event tracking

### For Admins:
- **Payout Management**: Review and process payout requests at `/admin`
- **Billing Statistics**: View platform revenue and transaction metrics
- **API Endpoints**:
  - `GET /api/admin/billing/payouts` - View all payout requests
  - `PUT /api/admin/billing/payouts/<id>` - Approve/reject payouts
  - `GET /api/admin/billing/stats` - Get billing statistics

## API Endpoints

### User Endpoints:
- `GET /billing` - Billing dashboard page
- `GET /api/billing/wallet` - Get wallet information
- `GET /api/billing/transactions` - Get transaction history
- `GET /api/billing/invoices` - Get invoices
- `GET /api/billing/payouts` - Get payout history
- `POST /api/billing/payouts` - Request a payout
- `GET /api/billing/payment-history` - Get detailed payment history
- `POST /api/billing/complete-gig/<gig_id>` - Complete a gig and create transaction with tiered commission

### Admin Endpoints:
- `GET /api/admin/billing/payouts` - Get all payout requests
- `PUT /api/admin/billing/payouts/<id>` - Update payout status
- `GET /api/admin/billing/stats` - Get billing statistics

## Database Schema

### Wallet Table
- Stores user wallet balances
- Tracks total earnings and spending
- Manages held balances for pending payouts

### Invoice Table
- Generates invoices for completed transactions
- Tracks payment status and methods
- Links to transactions and gigs

### Payout Table
- Manages freelancer payout requests
- Supports multiple payment methods (Bank, Touch 'n Go, GrabPay, Boost)
- Tracks processing status and completion

### Payment History Table
- Comprehensive audit trail of all payment events
- Records balance changes
- Links to transactions, invoices, and payouts

## Payment Methods Supported

1. **Bank Transfer (FPX)** - Major Malaysian banks
2. **Touch 'n Go eWallet**
3. **GrabPay**
4. **Boost**

## Platform Fees

### Tiered Transaction Commission (Charged to Freelancers)

The platform uses a **tiered commission structure** based on transaction amount:

| Transaction Amount | Commission Rate | Example |
|-------------------|----------------|---------|
| **MYR 0 - 500** | **15%** | MYR 300 gig → MYR 45 fee, freelancer gets MYR 255 |
| **MYR 501 - 2,000** | **10%** | MYR 1,500 gig → MYR 150 fee, freelancer gets MYR 1,350 |
| **MYR 2,001+** | **5%** | MYR 5,000 gig → MYR 250 fee, freelancer gets MYR 4,750 |

**How it works:**
- Client pays the full amount (e.g., MYR 1,000)
- Platform automatically calculates commission based on the tier
- Freelancer receives the net amount after commission
- Invoice and transaction records show the breakdown

### Payout Fee

- **2% of withdrawal amount** (charged when freelancers withdraw earnings)
- Example: Withdraw MYR 500 → MYR 10 fee, receive MYR 490

## Notes

- Minimum payout amount: MYR 10.00
- Maximum payout amount: MYR 10,000.00
- Payout processing time: 1-3 business days
- All amounts are in Malaysian Ringgit (MYR)

## Deployment

After running the SQL migration:
1. Commit the changes to your repository
2. Push to Railway
3. The app will automatically redeploy with the new billing features
4. Users can access the billing dashboard at `/billing`
5. Admins can manage payouts from the admin dashboard

## Security Features

- Login required for all billing pages
- User can only access their own billing data
- Admin-only access for payout management
- Secure balance calculations and validations
- Transaction history audit trail

---

For questions or issues, please check the application logs or contact support.
