# Password Reset Migration Fix

## Problem

The gunicorn server was crashing on startup with the following error:

```
Database initialization error: (psycopg2.errors.UndefinedColumn) column user.password_reset_token does not exist
```

## Root Cause

There was a chicken-and-egg problem with the database initialization:

1. When `app.py` is imported, it runs `init_database()` at module level (line 14886)
2. `init_database()` tries to count users with `User.query.count()` (line 12633)
3. SQLAlchemy tries to SELECT all columns from the user table, including `password_reset_token` and `password_reset_expires`
4. These columns don't exist yet because the migration hasn't run
5. The import fails, preventing gunicorn from starting
6. Since gunicorn can't start, the entrypoint.sh migration can't run either

## Solution

### 1. Updated `migrations/run_password_reset_migration.py`

- Removed dependency on importing from `app.py`
- Now uses `DATABASE_URL` environment variable directly
- Connects to the database using `psycopg2` (PostgreSQL) or `sqlite3` (SQLite)
- Can run before the app starts, breaking the circular dependency

### 2. Updated `app.py` init_database() function

- Added try-except block around `User.query.count()`
- If the query fails (due to missing columns), initialization is skipped gracefully
- Allows the app to start even with incomplete schema
- Migrations can then run and complete the schema

### 3. Created `migrations/run_migration_simple.py`

- Alternative standalone migration script
- Can be run independently with just the DATABASE_URL environment variable
- Useful for manual migration execution

## Testing the Fix

After deploying this fix, the application should:

1. Start successfully with gunicorn
2. Run the password reset migration automatically via entrypoint.sh
3. Add the missing columns to the user table
4. Continue normal operation

## Verifying the Migration

To verify that the migration was successful, check the logs for:

```
============================================================
GigHala Password Reset Fields Migration
============================================================

📊 Detected database type: POSTGRESQL
✅ Connected to postgresql database
🔧 Running PostgreSQL migration...
✅ PostgreSQL migration completed successfully!

🔍 Verifying migration...
✅ Column 'user.password_reset_token' exists
✅ Column 'user.password_reset_expires' exists

✅ Migration verified successfully!
```

## Manual Migration (if needed)

If the automatic migration doesn't run, you can run it manually:

```bash
# Using the updated migration script
python migrations/run_password_reset_migration.py

# Or using the simple standalone script
export DATABASE_URL='postgresql://user:pass@host:port/dbname'
python migrations/run_migration_simple.py
```

## Files Changed

- `migrations/run_password_reset_migration.py` - Updated to not import from app.py
- `app.py` - Added error handling in init_database()
- `migrations/run_migration_simple.py` - New standalone migration script (optional)
- `migrations/013_add_password_reset.sql` - SQL migration (unchanged, created previously)

## Related Pull Requests

- Previous PR: #178 (Add database migration for password reset fields)
- This PR: Fixes the migration execution issue
