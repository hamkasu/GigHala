# Migration: Add agreed_amount Column to Gig Table

## Problem

The application code references a `gig.agreed_amount` column that doesn't exist in the database, causing this error:

```
psycopg2.errors.UndefinedColumn: column gig.agreed_amount does not exist
```

## Solution

This migration adds the missing `agreed_amount` column to the `gig` table.

## Files Created

- `/migrations/002_add_agreed_amount.sql` - PostgreSQL migration
- `/migrations/002_add_agreed_amount_sqlite.sql` - SQLite migration
- `/migrate_add_agreed_amount.py` - Python migration script (recommended)

## How to Run

### Option 1: Using Python Script (Recommended)

Run the migration script from the application directory:

```bash
python3 migrate_add_agreed_amount.py
```

This script:
- Automatically detects your database type (PostgreSQL or SQLite)
- Checks if the column already exists
- Adds the column if needed
- Verifies the migration succeeded

### Option 2: In Railway Container

If your app is deployed on Railway:

```bash
# SSH into your Railway container
railway run python3 migrate_add_agreed_amount.py
```

Or use Railway's dashboard to run a one-off command.

### Option 3: Direct SQL (PostgreSQL)

Connect to your PostgreSQL database and run:

```sql
ALTER TABLE gig ADD COLUMN agreed_amount NUMERIC(10, 2);
```

### Option 4: Direct SQL (SQLite)

Connect to your SQLite database and run:

```sql
ALTER TABLE gig ADD COLUMN agreed_amount REAL;
```

## What This Migration Does

1. Adds an `agreed_amount` column to the `gig` table
2. Column type:
   - PostgreSQL: `NUMERIC(10, 2)` (allows up to 99,999,999.99)
   - SQLite: `REAL` (floating point number)
3. Column is nullable (can be NULL)
4. Creates an index on the column for better query performance (PostgreSQL only)

## Verification

After running the migration, verify it succeeded:

**PostgreSQL:**
```sql
\d gig
-- or
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'gig' AND column_name = 'agreed_amount';
```

**SQLite:**
```sql
PRAGMA table_info(gig);
```

You should see the `agreed_amount` column listed.

## After Migration

Once the migration is applied, restart your application. The error should be resolved.

## Rollback (if needed)

If you need to remove the column:

**PostgreSQL:**
```sql
ALTER TABLE gig DROP COLUMN agreed_amount;
```

**SQLite:**
```sql
-- SQLite doesn't support DROP COLUMN directly
-- You would need to recreate the table without the column
```

## Related

- Model definition: `app.py:917` - `agreed_amount = db.Column(db.Float)`
- This column tracks the negotiated payment amount when a freelancer is assigned to a gig
