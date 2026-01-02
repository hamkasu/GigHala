# Quick Setup: Database Role Separation

## 🚀 Copy-Paste SQL Commands

Run these commands **as the PostgreSQL superuser** to set up database role separation.

---

## Step 1: Generate Passwords

```bash
# Generate two strong passwords
openssl rand -base64 32  # Use this for gighala_admin
openssl rand -base64 32  # Use this for gighala_app
```

**Save these passwords!** You'll need them for your `.env` file.

---

## Step 2: Connect to Database

```bash
# Connect as superuser
psql $DATABASE_URL

# Or for Railway
railway run psql $DATABASE_URL
```

---

## Step 3: Run These SQL Commands

**Copy and paste the entire block below** (replace passwords):

```sql
-- ============================================
-- CREATE ROLES (replace passwords!)
-- ============================================
CREATE ROLE gighala_admin WITH LOGIN PASSWORD 'YOUR_ADMIN_PASSWORD_HERE';
CREATE ROLE gighala_app WITH LOGIN PASSWORD 'YOUR_APP_PASSWORD_HERE';

-- ============================================
-- GRANT DATABASE PRIVILEGES
-- ============================================
GRANT ALL PRIVILEGES ON DATABASE gighala TO gighala_admin;
GRANT CONNECT ON DATABASE gighala TO gighala_app;

-- ============================================
-- GRANT SCHEMA PRIVILEGES
-- ============================================
GRANT ALL ON SCHEMA public TO gighala_admin;
GRANT USAGE ON SCHEMA public TO gighala_app;

-- ============================================
-- GRANT TABLE PRIVILEGES
-- ============================================
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO gighala_admin;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO gighala_app;

-- ============================================
-- GRANT SEQUENCE PRIVILEGES
-- ============================================
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO gighala_admin;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO gighala_app;

-- ============================================
-- SET DEFAULT PRIVILEGES FOR FUTURE OBJECTS
-- ============================================
ALTER DEFAULT PRIVILEGES FOR ROLE gighala_admin IN SCHEMA public
GRANT ALL PRIVILEGES ON TABLES TO gighala_admin;

ALTER DEFAULT PRIVILEGES FOR ROLE gighala_admin IN SCHEMA public
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO gighala_app;

ALTER DEFAULT PRIVILEGES FOR ROLE gighala_admin IN SCHEMA public
GRANT ALL PRIVILEGES ON SEQUENCES TO gighala_admin;

ALTER DEFAULT PRIVILEGES FOR ROLE gighala_admin IN SCHEMA public
GRANT USAGE, SELECT ON SEQUENCES TO gighala_app;

ALTER DEFAULT PRIVILEGES FOR ROLE gighala_admin IN SCHEMA public
GRANT ALL PRIVILEGES ON FUNCTIONS TO gighala_admin;

ALTER DEFAULT PRIVILEGES FOR ROLE gighala_admin IN SCHEMA public
GRANT EXECUTE ON FUNCTIONS TO gighala_app;
```

---

## Step 4: Verify Setup

```sql
-- Check roles were created
SELECT rolname, rolsuper FROM pg_roles WHERE rolname LIKE 'gighala%';

-- Expected output:
--     rolname     | rolsuper
-- ----------------+----------
--  gighala_admin  | f
--  gighala_app    | f
```

---

## Step 5: Update Environment Variables

Add to your `.env` file or hosting platform (Railway, Heroku, etc.):

```bash
# App connection (limited privileges) - used by production app
DATABASE_URL=postgresql://gighala_app:YOUR_APP_PASSWORD@host:5432/gighala

# Admin connection (full privileges) - used for migrations ONLY
DATABASE_ADMIN_URL=postgresql://gighala_admin:YOUR_ADMIN_PASSWORD@host:5432/gighala
```

**Replace:**
- `YOUR_APP_PASSWORD` - Password you set for gighala_app
- `YOUR_ADMIN_PASSWORD` - Password you set for gighala_admin
- `host` - Your database host (e.g., `localhost` or Railway hostname)
- `gighala` - Your database name (change if different)

---

## Step 6: Test It Works

```bash
# Test app connection (should work)
psql "postgresql://gighala_app:YOUR_APP_PASSWORD@host:5432/gighala" -c "SELECT COUNT(*) FROM \"user\";"

# Test app CANNOT drop tables (should fail with permission error - this is good!)
psql "postgresql://gighala_app:YOUR_APP_PASSWORD@host:5432/gighala" -c "DROP TABLE \"user\";"
# Expected: ERROR: must be owner of table user
```

✅ If you get the permission error, it's working correctly!

---

## That's It! 🎉

Your database now follows the **Principle of Least Privilege**.

### What You Achieved:

✅ **gighala_app** - Limited privileges (can't DROP tables)
✅ **gighala_admin** - Full privileges (for migrations only)
✅ **Better security** - Stolen credentials can't destroy your database
✅ **Compliance** - Meets security audit standards

---

## Next Steps

1. Update your production environment variables
2. Restart your application (it will use the limited `gighala_app` role)
3. For migrations, use: `psql $DATABASE_ADMIN_URL -f migrations/file.sql`

---

## Need More Details?

See the comprehensive guide: `DATABASE_SECURITY_SETUP.md`

---

## Database Name Different?

If your database is named something other than `gighala`, replace it in:
- All `GRANT` commands: `ON DATABASE gighala` → `ON DATABASE your_db_name`
- Connection strings: `@host:5432/gighala` → `@host:5432/your_db_name`
