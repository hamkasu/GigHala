# Database Migration Guide - Invoice & Receipt Workflow

This guide explains how to update your database to support the new invoice and receipt workflow for job completion.

## Quick Start

### Option 1: Automatic Migration (Recommended)

Run the Python migration script which auto-detects your database type:

```bash
python3 migrations/run_migration.py
```

This script will:
- ✅ Detect whether you're using SQLite or PostgreSQL
- ✅ Create all necessary tables and columns
- ✅ Add performance indexes
- ✅ Verify the migration was successful
- ✅ Show you a summary of changes

### Option 2: Flask-SQLAlchemy Auto-Create

If you have a fresh database or want to recreate all tables:

```bash
python3 << EOF
from app import app, db
with app.app_context():
    db.create_all()
    print("✅ All tables created successfully!")
EOF
```

### Option 3: Manual SQL Execution

#### For PostgreSQL:
```bash
psql $DATABASE_URL < migrations/001_invoice_receipt_workflow.sql
```

#### For SQLite:
```bash
sqlite3 gighala.db < migrations/001_invoice_receipt_workflow_sqlite.sql
```

## What Gets Updated?

### 1. Invoice Table
Tracks invoices issued to clients when workers complete jobs.

**Key columns:**
- `invoice_number` - Unique identifier (e.g., INV-20251218-12345)
- `status` - Payment status (issued → paid)
- `due_date` - When payment is due (default: 7 days)
- `paid_at` - Timestamp when invoice was paid
- `payment_reference` - Payment gateway reference
- `notes` - Additional invoice notes

### 2. Receipt Table
Stores payment receipts for completed transactions.

**Key columns:**
- `receipt_number` - Unique identifier (e.g., PAY-RCP-20251218-67890)
- `receipt_type` - Type: payment, escrow_funding, refund, payout
- `invoice_id` - Links receipt to invoice
- `description` - Human-readable description

### 3. Notification Table
Enhanced to support invoice/receipt notifications.

**New columns:**
- `related_id` - ID of related entity (invoice_id, receipt_id, etc.)
- `link` - Deep link to invoice/receipt view

### 4. Performance Indexes
Indexes are added on frequently queried columns for faster lookups.

## Workflow After Migration

Once migrated, the system works as follows:

```
1. Worker completes job
   └─> POST /api/gigs/{id}/submit-work
       └─> Creates Invoice (status: 'issued')
       └─> Notifies client and worker with invoice link

2. Client approves work
   └─> POST /api/gigs/{id}/approve-work
       └─> Marks gig as completed
       └─> Reminds client to release payment

3. Client releases escrow payment
   └─> POST /api/escrow/{id}/release
       └─> Marks Invoice as 'paid'
       └─> Creates Receipt
       └─> Notifies both parties with receipt link
       └─> Transfers funds to worker wallet
```

## Verifying the Migration

After running the migration, verify it worked:

```bash
# For PostgreSQL
psql $DATABASE_URL -c "\d invoice"
psql $DATABASE_URL -c "\d receipt"
psql $DATABASE_URL -c "\d notification"

# For SQLite
sqlite3 gighala.db ".schema invoice"
sqlite3 gighala.db ".schema receipt"
sqlite3 gighala.db ".schema notification"
```

## Rollback (If Needed)

If you need to undo the migration:

### For PostgreSQL:
```sql
DROP INDEX IF EXISTS idx_invoice_gig_id;
DROP INDEX IF EXISTS idx_invoice_client_id;
DROP INDEX IF EXISTS idx_invoice_freelancer_id;
-- ... (drop other indexes)

-- Only if you want to remove the tables entirely:
-- DROP TABLE IF EXISTS receipt CASCADE;
-- DROP TABLE IF EXISTS invoice CASCADE;
```

### For SQLite:
```sql
DROP INDEX IF EXISTS idx_invoice_gig_id;
DROP INDEX IF EXISTS idx_invoice_client_id;
-- ... (drop other indexes)

-- Only if you want to remove the tables entirely:
-- DROP TABLE IF EXISTS receipt;
-- DROP TABLE IF EXISTS invoice;
```

**Note:** Dropping tables will delete all invoice and receipt data. Only do this if absolutely necessary.

## Troubleshooting

### Error: "relation already exists"
This is normal if the table was already created by Flask-SQLAlchemy. The migration is idempotent and will skip existing tables.

### Error: "column already exists"
Also normal for existing databases. The migration checks for existing columns before adding them (PostgreSQL only).

### SQLite: "Cannot add column with constraints"
SQLite has limitations on ALTER TABLE. If you encounter this:

1. **Option A:** Use Flask-SQLAlchemy's `db.create_all()` which handles SQLite properly
2. **Option B:** Manually recreate the tables (backup data first!)

### Missing columns in SQLite
If columns are missing after migration:

```python
# Run this in Python shell
from app import app, db
from sqlalchemy import text

with app.app_context():
    # Add missing columns manually
    db.session.execute(text("ALTER TABLE invoice ADD COLUMN due_date DATETIME"))
    db.session.execute(text("ALTER TABLE invoice ADD COLUMN paid_at DATETIME"))
    db.session.execute(text("ALTER TABLE receipt ADD COLUMN invoice_id INTEGER"))
    db.session.commit()
```

## Production Deployment

For production environments:

1. **Backup your database first!**
   ```bash
   # PostgreSQL
   pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql

   # SQLite
   sqlite3 gighala.db ".backup 'backup_$(date +%Y%m%d).db'"
   ```

2. **Run migration in maintenance window**
   - Put site in maintenance mode
   - Run migration script
   - Verify migration
   - Test invoice/receipt creation
   - Bring site back online

3. **Monitor for issues**
   - Check application logs
   - Test job completion workflow end-to-end
   - Verify invoices and receipts are created correctly

## Getting Help

If you encounter issues:

1. Check the migration logs for specific error messages
2. Verify your database connection string is correct
3. Ensure you have proper database permissions
4. Review the migration SQL files in `migrations/` directory
5. Check the README.md in the migrations folder

## Next Steps

After successful migration:

1. ✅ Test the workflow: Create a test gig, submit work, approve, and release payment
2. ✅ Verify invoices are created at `/invoices`
3. ✅ Verify receipts are created at `/billing`
4. ✅ Check notifications are sent to both parties
5. ✅ Review invoice and receipt templates for branding

Your database is now ready for the enhanced invoice and receipt workflow! 🎉
