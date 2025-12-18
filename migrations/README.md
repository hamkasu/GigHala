# Database Migrations

This directory contains SQL migration scripts for the GigHala platform.

## Migration Files

### 001_invoice_receipt_workflow.sql (PostgreSQL)
Adds invoice and receipt workflow support for job completion.

**Features:**
- Creates/updates Invoice table with payment tracking
- Creates/updates Receipt table for payment receipts
- Creates/updates Notification table with related_id support
- Adds performance indexes on key columns
- Fully idempotent - safe to run multiple times

**To apply (PostgreSQL):**
```bash
psql $DATABASE_URL < migrations/001_invoice_receipt_workflow.sql
```

### 001_invoice_receipt_workflow_sqlite.sql (SQLite)
SQLite version of the invoice and receipt workflow migration.

**To apply (SQLite):**
```bash
sqlite3 gighalal.db < migrations/001_invoice_receipt_workflow_sqlite.sql
```

## Using Flask-SQLAlchemy

If you prefer to use Flask-SQLAlchemy's automatic table creation:

```python
# In your Flask app or Python shell
from app import db
db.create_all()
```

This will automatically create all tables based on the models defined in `app.py`.

## Manual Column Addition (SQLite)

If you have an existing SQLite database and need to add missing columns:

1. **Check existing columns:**
   ```sql
   PRAGMA table_info(invoice);
   ```

2. **Add missing columns one by one:**
   ```sql
   ALTER TABLE invoice ADD COLUMN due_date DATETIME;
   ALTER TABLE invoice ADD COLUMN paid_at DATETIME;
   ALTER TABLE invoice ADD COLUMN payment_reference VARCHAR(100);
   ALTER TABLE invoice ADD COLUMN notes TEXT;

   ALTER TABLE receipt ADD COLUMN invoice_id INTEGER REFERENCES invoice(id);
   ALTER TABLE receipt ADD COLUMN description TEXT;

   ALTER TABLE notification ADD COLUMN related_id INTEGER;
   ALTER TABLE notification ADD COLUMN link VARCHAR(500);
   ```

## Using Alembic (Recommended for Production)

For production environments, consider using Alembic for database migrations:

```bash
# Install Alembic
pip install alembic

# Initialize Alembic
alembic init alembic

# Create a migration
alembic revision --autogenerate -m "Add invoice receipt workflow"

# Apply migration
alembic upgrade head
```

## Database Schema Changes

### Invoice Table
- `invoice_number`: Unique invoice identifier
- `status`: draft | issued | paid | cancelled | refunded
- `due_date`: Payment due date (default: 7 days from creation)
- `paid_at`: Timestamp when invoice was marked as paid
- `payment_reference`: Reference number from payment gateway
- `notes`: Additional notes about the invoice

### Receipt Table
- `receipt_number`: Unique receipt identifier
- `receipt_type`: escrow_funding | payment | refund | payout
- `invoice_id`: Links receipt to the invoice it settles
- `description`: Human-readable description of the receipt

### Notification Table
- `related_id`: ID of related entity (gig_id, invoice_id, receipt_id, etc.)
- `link`: Deep link URL to the relevant page in the application

## Workflow

1. **Worker submits work** → Invoice created (status: 'issued')
2. **Client approves work** → Gig marked as completed
3. **Client releases payment** → Invoice marked as 'paid' + Receipt created
4. Both parties receive notifications at each step with links to invoices/receipts

## Indexes Added

For optimal query performance, the following indexes are created:

**Invoice table:**
- `idx_invoice_gig_id` - Fast lookups by gig
- `idx_invoice_client_id` - Fast lookups by client
- `idx_invoice_freelancer_id` - Fast lookups by freelancer
- `idx_invoice_status` - Filter by payment status
- `idx_invoice_created_at` - Sort by date

**Receipt table:**
- `idx_receipt_gig_id` - Fast lookups by gig
- `idx_receipt_user_id` - Fast lookups by user
- `idx_receipt_invoice_id` - Link receipts to invoices
- `idx_receipt_escrow_id` - Link receipts to escrow
- `idx_receipt_type` - Filter by receipt type

**Notification table:**
- `idx_notification_user_id` - Fast user notification queries
- `idx_notification_type` - Filter by notification type
- `idx_notification_is_read` - Unread notification queries
- `idx_notification_related_id` - Link to related entities
