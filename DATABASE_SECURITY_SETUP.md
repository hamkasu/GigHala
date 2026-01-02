# Database Security Setup Guide
## Implementing Principle of Least Privilege for GigHala

This guide walks you through setting up proper database role separation for GigHala, implementing the **Principle of Least Privilege** security best practice.

---

## Table of Contents
1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Manual Setup Steps](#manual-setup-steps)
4. [Verification](#verification)
5. [Updating Your Application](#updating-your-application)
6. [Troubleshooting](#troubleshooting)

---

## Overview

### What This Does

Creates two separate database roles:

| Role | Purpose | Privileges | When to Use |
|------|---------|-----------|-------------|
| `gighala_admin` | Migrations & maintenance | Full (CREATE, DROP, ALTER) | Running migrations only |
| `gighala_app` | Production runtime | Limited (SELECT, INSERT, UPDATE, DELETE) | Production application |

### Security Benefits

✅ **Prevents accidental damage** - App bugs can't DROP tables
✅ **Limits breach impact** - Stolen credentials can't destroy schema
✅ **Compliance** - Meets security audit requirements
✅ **Defense in depth** - Multiple layers of protection

---

## Prerequisites

- PostgreSQL database (already set up)
- Superuser access (`postgres` user) or database owner privileges
- `psql` command-line tool installed
- Your current `DATABASE_URL` connection string

---

## Manual Setup Steps

### Step 1: Generate Strong Passwords

Generate two strong passwords for the new roles:

```bash
# Generate admin password (use this for gighala_admin)
openssl rand -base64 32

# Generate app password (use this for gighala_app)
openssl rand -base64 32
```

**Save these passwords securely!** You'll need them for your environment variables.

---

### Step 2: Connect as Superuser

Connect to your PostgreSQL database as the superuser or owner:

```bash
# Using your current DATABASE_URL
psql $DATABASE_URL

# OR connect as postgres superuser
psql -U postgres -d gighala

# OR for Railway
railway run psql $DATABASE_URL
```

---

### Step 3: Create Database Roles

Run these commands **one at a time** in the `psql` prompt:

```sql
-- Create admin role (replace PASSWORD with your generated password)
CREATE ROLE gighala_admin WITH LOGIN PASSWORD 'YOUR_ADMIN_PASSWORD_HERE';

-- Create app role (replace PASSWORD with your generated password)
CREATE ROLE gighala_app WITH LOGIN PASSWORD 'YOUR_APP_PASSWORD_HERE';
```

**Expected output:**
```
CREATE ROLE
CREATE ROLE
```

---

### Step 4: Grant Database-Level Privileges

```sql
-- Admin gets full privileges
GRANT ALL PRIVILEGES ON DATABASE gighala TO gighala_admin;

-- App gets connection privileges
GRANT CONNECT ON DATABASE gighala TO gighala_app;
```

**Note:** Replace `gighala` with your actual database name if different.

---

### Step 5: Grant Schema Privileges

```sql
-- Admin gets full schema privileges
GRANT ALL ON SCHEMA public TO gighala_admin;

-- App gets usage on public schema
GRANT USAGE ON SCHEMA public TO gighala_app;
```

---

### Step 6: Grant Table Privileges

```sql
-- Admin gets all privileges on all existing tables
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO gighala_admin;

-- App gets limited privileges (SELECT, INSERT, UPDATE, DELETE only)
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO gighala_app;
```

---

### Step 7: Grant Sequence Privileges

```sql
-- Admin gets all privileges on sequences
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO gighala_admin;

-- App needs sequences for auto-increment IDs
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO gighala_app;
```

---

### Step 8: Set Default Privileges for Future Tables

This ensures new tables created by `gighala_admin` automatically grant privileges to `gighala_app`:

```sql
-- Future tables created by admin
ALTER DEFAULT PRIVILEGES FOR ROLE gighala_admin IN SCHEMA public
GRANT ALL PRIVILEGES ON TABLES TO gighala_admin;

ALTER DEFAULT PRIVILEGES FOR ROLE gighala_admin IN SCHEMA public
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO gighala_app;

-- Future sequences created by admin
ALTER DEFAULT PRIVILEGES FOR ROLE gighala_admin IN SCHEMA public
GRANT ALL PRIVILEGES ON SEQUENCES TO gighala_admin;

ALTER DEFAULT PRIVILEGES FOR ROLE gighala_admin IN SCHEMA public
GRANT USAGE, SELECT ON SEQUENCES TO gighala_app;

-- Future functions created by admin
ALTER DEFAULT PRIVILEGES FOR ROLE gighala_admin IN SCHEMA public
GRANT ALL PRIVILEGES ON FUNCTIONS TO gighala_admin;

ALTER DEFAULT PRIVILEGES FOR ROLE gighala_admin IN SCHEMA public
GRANT EXECUTE ON FUNCTIONS TO gighala_app;
```

---

### Step 9: (OPTIONAL) Transfer Ownership

If you want to transfer ownership of existing tables to `gighala_admin`:

```sql
-- Transfer table ownership
DO $$
DECLARE
    tbl record;
BEGIN
    FOR tbl IN
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'public'
    LOOP
        EXECUTE 'ALTER TABLE public.' || quote_ident(tbl.tablename) || ' OWNER TO gighala_admin';
    END LOOP;
END $$;

-- Transfer sequence ownership
DO $$
DECLARE
    seq record;
BEGIN
    FOR seq IN
        SELECT sequencename
        FROM pg_sequences
        WHERE schemaname = 'public'
    LOOP
        EXECUTE 'ALTER SEQUENCE public.' || quote_ident(seq.sequencename) || ' OWNER TO gighala_admin';
    END LOOP;
END $$;
```

---

## Verification

### Verify Roles Were Created

```sql
-- Check roles exist
SELECT rolname, rolsuper, rolcreaterole, rolcreatedb
FROM pg_roles
WHERE rolname LIKE 'gighala%';
```

**Expected output:**
```
     rolname     | rolsuper | rolcreaterole | rolcreatedb
-----------------+----------+---------------+-------------
 gighala_admin   | f        | f             | f
 gighala_app     | f        | f             | f
(2 rows)
```

---

### Verify Table Privileges for gighala_app

```sql
-- Check what privileges gighala_app has
SELECT table_name, privilege_type
FROM information_schema.role_table_grants
WHERE grantee = 'gighala_app'
ORDER BY table_name, privilege_type;
```

**Expected output:** Should show SELECT, INSERT, UPDATE, DELETE for each table
**Should NOT show:** TRUNCATE, REFERENCES, TRIGGER

---

### Verify Sequence Privileges

```sql
-- Check sequence privileges
SELECT object_name, privilege_type
FROM information_schema.usage_privileges
WHERE grantee = 'gighala_app' AND object_type = 'SEQUENCE';
```

**Expected output:** Should show USAGE for all sequences

---

### Test Connection as gighala_app

Exit `psql` and test connecting with the new app role:

```bash
# Test gighala_app connection
psql "postgresql://gighala_app:YOUR_APP_PASSWORD@host:5432/gighala" -c "SELECT COUNT(*) FROM \"user\";"
```

**Expected:** Should return count successfully

```bash
# Verify gighala_app CANNOT drop tables (should fail)
psql "postgresql://gighala_app:YOUR_APP_PASSWORD@host:5432/gighala" -c "DROP TABLE \"user\";"
```

**Expected error:**
```
ERROR:  must be owner of table user
```

✅ **This is correct!** The app role can't drop tables.

---

## Updating Your Application

### Step 1: Update Environment Variables

Update your `.env` file or hosting platform environment variables:

**For Production (Railway, Heroku, etc.):**

```bash
# Application runtime connection (LIMITED PRIVILEGES)
DATABASE_URL=postgresql://gighala_app:YOUR_APP_PASSWORD@host:5432/gighala

# Admin connection for migrations (FULL PRIVILEGES - keep secure!)
DATABASE_ADMIN_URL=postgresql://gighala_admin:YOUR_ADMIN_PASSWORD@host:5432/gighala
```

**For Local Development:**

Add to your `.env` file:
```
DATABASE_URL=postgresql://gighala_app:YOUR_APP_PASSWORD@localhost:5432/gighala
DATABASE_ADMIN_URL=postgresql://gighala_admin:YOUR_ADMIN_PASSWORD@localhost:5432/gighala
```

---

### Step 2: Running Migrations

**From now on, use `DATABASE_ADMIN_URL` for migrations:**

```bash
# Run migrations with admin privileges
psql $DATABASE_ADMIN_URL -f migrations/012_database_role_separation.sql

# For Python migration scripts
export DATABASE_URL=$DATABASE_ADMIN_URL
python migrations/run_migration.py
```

---

### Step 3: Verify Application Still Works

```bash
# Start your application (should use DATABASE_URL with gighala_app)
python app.py

# Test basic operations:
# - Register a new user
# - Login
# - Create a gig
# - Apply to a gig
```

---

## Troubleshooting

### Problem: "permission denied for table X"

**Cause:** `gighala_app` missing privileges on a specific table

**Fix:**
```sql
-- Grant missing privileges
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE specific_table TO gighala_app;
```

---

### Problem: "permission denied for sequence X_id_seq"

**Cause:** `gighala_app` can't use auto-increment sequences

**Fix:**
```sql
-- Grant sequence access
GRANT USAGE, SELECT ON SEQUENCE specific_table_id_seq TO gighala_app;
```

---

### Problem: Migration fails with "permission denied"

**Cause:** Using `DATABASE_URL` instead of `DATABASE_ADMIN_URL`

**Fix:**
```bash
# Use admin URL for migrations
psql $DATABASE_ADMIN_URL -f migrations/your_migration.sql
```

---

### Problem: Need to grant privileges on all tables quickly

**Fix:**
```sql
-- Re-run grants
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO gighala_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO gighala_app;
```

---

## Quick Reference: SQL Commands

### Create Roles
```sql
CREATE ROLE gighala_admin WITH LOGIN PASSWORD 'admin_password';
CREATE ROLE gighala_app WITH LOGIN PASSWORD 'app_password';
```

### Grant All Privileges (Admin)
```sql
GRANT ALL PRIVILEGES ON DATABASE gighala TO gighala_admin;
GRANT ALL ON SCHEMA public TO gighala_admin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO gighala_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO gighala_admin;
```

### Grant Limited Privileges (App)
```sql
GRANT CONNECT ON DATABASE gighala TO gighala_app;
GRANT USAGE ON SCHEMA public TO gighala_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO gighala_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO gighala_app;
```

### Set Default Privileges
```sql
ALTER DEFAULT PRIVILEGES FOR ROLE gighala_admin IN SCHEMA public
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO gighala_app;

ALTER DEFAULT PRIVILEGES FOR ROLE gighala_admin IN SCHEMA public
GRANT USAGE, SELECT ON SEQUENCES TO gighala_app;
```

---

## Connection String Format

```
# App connection (limited privileges)
postgresql://gighala_app:password@host:port/database

# Admin connection (full privileges)
postgresql://gighala_admin:password@host:port/database
```

**Replace:**
- `password` - Your generated password
- `host` - Database host (e.g., `localhost`, Railway hostname)
- `port` - Usually `5432`
- `database` - Usually `gighala`

---

## Security Best Practices

✅ **DO:**
- Use `gighala_app` credentials in production application
- Use `gighala_admin` only for migrations
- Store credentials in environment variables
- Use different passwords for each role
- Rotate passwords periodically
- Keep `DATABASE_ADMIN_URL` secure and separate from app configs

❌ **DON'T:**
- Hardcode database credentials in code
- Use admin credentials in production app
- Share admin credentials with team members unnecessarily
- Store credentials in version control
- Use weak or default passwords

---

## Next Steps

1. ✅ Complete manual setup above
2. ✅ Update environment variables
3. ✅ Test application functionality
4. ✅ Run new migrations with admin credentials
5. ✅ Update your deployment documentation
6. 🔒 Store admin credentials securely (1Password, AWS Secrets Manager, etc.)

---

## Need Help?

- Check [PostgreSQL GRANT documentation](https://www.postgresql.org/docs/current/sql-grant.html)
- Review GigHala's `SECURITY_AUDIT_REPORT.md`
- Test privileges with `information_schema.role_table_grants`

**Your database is now more secure! 🔒**
