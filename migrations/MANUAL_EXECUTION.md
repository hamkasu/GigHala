# Manual Database Migration - Quick Guide

This guide shows you how to manually execute SQL queries to update your database.

## Choose Your Database Type

### 🐘 PostgreSQL

**Option 1: Using psql command line**
```bash
# Connect to your database
psql $DATABASE_URL

# Or if you have connection details:
psql -h hostname -U username -d database_name

# Execute the migration file
\i migrations/MANUAL_POSTGRESQL.sql

# Verify it worked
\i migrations/VERIFY.sql

# Exit
\q
```

**Option 2: Copy-paste into psql**
```bash
# Connect to your database
psql $DATABASE_URL

# Then copy the contents of MANUAL_POSTGRESQL.sql
# Paste into the psql terminal
# Press Enter to execute
```

**Option 3: Using pgAdmin**
1. Open pgAdmin
2. Connect to your database
3. Click Tools → Query Tool
4. Open `migrations/MANUAL_POSTGRESQL.sql`
5. Click Execute (F5)
6. Check the output for any errors

**Option 4: One-line command**
```bash
psql $DATABASE_URL < migrations/MANUAL_POSTGRESQL.sql
```

---

### 💾 SQLite

**Option 1: Using sqlite3 command line**
```bash
# Connect to your database
sqlite3 gighalal.db

# Execute the migration file
.read migrations/MANUAL_SQLITE.sql

# Verify it worked
.read migrations/VERIFY.sql

# Exit
.quit
```

**Option 2: Copy-paste into sqlite3**
```bash
# Connect to your database
sqlite3 gighalal.db

# Then copy the contents of MANUAL_SQLITE.sql
# Paste into the sqlite terminal
# Press Enter to execute
```

**Option 3: One-line command**
```bash
sqlite3 gighalal.db < migrations/MANUAL_SQLITE.sql
```

**Option 4: Using DB Browser for SQLite**
1. Open DB Browser for SQLite
2. Open your database file (gighalal.db)
3. Go to "Execute SQL" tab
4. Open `migrations/MANUAL_SQLITE.sql`
5. Click Execute

---

## Step-by-Step Manual Execution

If you prefer to run queries one by one:

### For PostgreSQL:

1. **Connect to database:**
   ```bash
   psql $DATABASE_URL
   ```

2. **Create Invoice table:**
   ```sql
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
   ```

3. **Create Receipt table:**
   ```sql
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
   ```

4. **Create indexes:**
   ```sql
   CREATE INDEX IF NOT EXISTS idx_invoice_gig_id ON invoice(gig_id);
   CREATE INDEX IF NOT EXISTS idx_invoice_client_id ON invoice(client_id);
   CREATE INDEX IF NOT EXISTS idx_receipt_gig_id ON receipt(gig_id);
   CREATE INDEX IF NOT EXISTS idx_receipt_invoice_id ON receipt(invoice_id);
   ```

5. **Verify:**
   ```sql
   \dt invoice
   \dt receipt
   \d invoice
   \d receipt
   ```

### For SQLite:

1. **Connect to database:**
   ```bash
   sqlite3 gighalal.db
   ```

2. **Create Invoice table:**
   ```sql
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
   ```

3. **Create Receipt table:**
   ```sql
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
   ```

4. **Create indexes:**
   ```sql
   CREATE INDEX IF NOT EXISTS idx_invoice_gig_id ON invoice(gig_id);
   CREATE INDEX IF NOT EXISTS idx_invoice_client_id ON invoice(client_id);
   CREATE INDEX IF NOT EXISTS idx_receipt_gig_id ON receipt(gig_id);
   CREATE INDEX IF NOT EXISTS idx_receipt_invoice_id ON receipt(invoice_id);
   ```

5. **Verify:**
   ```sql
   .tables
   .schema invoice
   .schema receipt
   PRAGMA table_info(invoice);
   PRAGMA table_info(receipt);
   ```

---

## Verification

After running the migration, verify everything worked:

### PostgreSQL:
```bash
psql $DATABASE_URL < migrations/VERIFY.sql
```

### SQLite:
```bash
sqlite3 gighalal.db < migrations/VERIFY.sql
```

Or manually check:
```sql
-- Check tables exist
SELECT * FROM invoice LIMIT 1;
SELECT * FROM receipt LIMIT 1;

-- Check columns exist
-- PostgreSQL:
\d invoice
\d receipt

-- SQLite:
PRAGMA table_info(invoice);
PRAGMA table_info(receipt);
```

---

## Troubleshooting

### Error: "relation already exists"
✅ This is fine! It means the table was already created. Skip to the next step.

### Error: "column already exists"
✅ This is fine! The column already exists. Skip to the next step.

### Error: "syntax error near..."
❌ Check that you're using the correct SQL file for your database type:
- PostgreSQL → use `MANUAL_POSTGRESQL.sql`
- SQLite → use `MANUAL_SQLITE.sql`

### Error: "no such table: user"
❌ Your database might not be fully initialized. Run:
```python
python3 -c "from app import app, db; app.app_context().push(); db.create_all()"
```

### SQLite: "Cannot add column with constraint"
SQLite has limitations. Instead:
```python
# Use Flask-SQLAlchemy
python3 -c "from app import app, db; app.app_context().push(); db.create_all()"
```

---

## Quick Command Reference

### PostgreSQL
```bash
# Execute all at once
psql $DATABASE_URL < migrations/MANUAL_POSTGRESQL.sql

# Execute interactively
psql $DATABASE_URL
\i migrations/MANUAL_POSTGRESQL.sql
\i migrations/VERIFY.sql
\q

# Check specific table
psql $DATABASE_URL -c "\d invoice"
```

### SQLite
```bash
# Execute all at once
sqlite3 gighalal.db < migrations/MANUAL_SQLITE.sql

# Execute interactively
sqlite3 gighalal.db
.read migrations/MANUAL_SQLITE.sql
.read migrations/VERIFY.sql
.quit

# Check specific table
sqlite3 gighalal.db ".schema invoice"
```

---

## What You Should See After Success

✅ **Invoice table** with columns: invoice_number, due_date, paid_at, payment_reference, notes
✅ **Receipt table** with columns: receipt_number, receipt_type, invoice_id, description
✅ **Notification table** with columns: related_id, link
✅ **Multiple indexes** on each table (5-6 per table)
✅ **No errors** in the output

---

## Need Help?

1. Check the error message carefully
2. Verify you're using the correct database type
3. Make sure your database is running and accessible
4. Check the main MIGRATION_GUIDE.md for more details
5. Try the Python migration script: `python3 migrations/run_migration.py`

---

## After Migration

Once complete, your database will support:
- ✅ Automatic invoice creation when workers complete jobs
- ✅ Receipt generation when clients pay
- ✅ Notifications to both parties with invoice/receipt links
- ✅ Payment tracking with invoice status (issued → paid)
