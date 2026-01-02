# Database Role Separation for Migrations

## Important: Use Admin Credentials for Migrations

Starting with migration `012_database_role_separation.sql`, GigHala implements the **Principle of Least Privilege** with separate database roles.

## Quick Reference

| Role | Purpose | Environment Variable |
|------|---------|---------------------|
| `gighala_app` | Production runtime | `DATABASE_URL` |
| `gighala_admin` | Migrations & maintenance | `DATABASE_ADMIN_URL` |

---

## Running SQL Migrations

### ✅ Correct Way (Using Admin Credentials)

```bash
# Use DATABASE_ADMIN_URL for migrations
psql $DATABASE_ADMIN_URL -f migrations/012_database_role_separation.sql
```

### ❌ Wrong Way (Will Fail)

```bash
# DON'T use DATABASE_URL - it has limited privileges
psql $DATABASE_URL -f migrations/012_database_role_separation.sql
# ERROR: permission denied to create role
```

---

## Running Python Migrations

### Method 1: Temporary Override

```bash
# Temporarily use admin URL for the migration
export DATABASE_URL=$DATABASE_ADMIN_URL
python migrations/run_migration.py
```

### Method 2: Update Migration Script

Modify your Python migration scripts to check for `DATABASE_ADMIN_URL`:

```python
import os
from sqlalchemy import create_engine

# Check for admin URL first, fall back to regular URL
database_url = os.environ.get('DATABASE_ADMIN_URL') or os.environ.get('DATABASE_URL')

if not database_url:
    raise ValueError("DATABASE_URL or DATABASE_ADMIN_URL must be set")

# Convert postgres:// to postgresql://
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

engine = create_engine(database_url)

# Run your migration
with engine.connect() as conn:
    # Your migration code here
    conn.execute(text("ALTER TABLE..."))
    conn.commit()
```

---

## Railway Deployment

### Setting Up Environment Variables

In Railway dashboard:

1. Go to your project → Variables
2. Add both variables:
   ```
   DATABASE_URL=postgresql://gighala_app:APP_PASSWORD@host:5432/railway
   DATABASE_ADMIN_URL=postgresql://gighala_admin:ADMIN_PASSWORD@host:5432/railway
   ```

### Running Migrations on Railway

```bash
# Use Railway CLI with admin URL
railway run --service postgres psql $DATABASE_ADMIN_URL -f migrations/012_database_role_separation.sql

# Or set environment variable temporarily
railway run bash -c "export DATABASE_URL=\$DATABASE_ADMIN_URL && python migrations/run_migration.py"
```

---

## Local Development

### Setup

```bash
# Add to your .env file
DATABASE_URL=postgresql://gighala_app:app_pass@localhost:5432/gighala
DATABASE_ADMIN_URL=postgresql://gighala_admin:admin_pass@localhost:5432/gighala
```

### Running Migrations Locally

```bash
# Load .env and run migration
source .env  # or use python-dotenv
psql $DATABASE_ADMIN_URL -f migrations/012_database_role_separation.sql
```

---

## Migration Checklist

Before running a migration:

- [ ] Migration creates or alters tables? → **Use DATABASE_ADMIN_URL**
- [ ] Migration only inserts/updates data? → **Can use DATABASE_URL**
- [ ] Migration creates functions/triggers? → **Use DATABASE_ADMIN_URL**
- [ ] Migration grants privileges? → **Use DATABASE_ADMIN_URL** (requires superuser)

**Rule of thumb:** If you're unsure, use `DATABASE_ADMIN_URL` for migrations.

---

## Troubleshooting

### Error: "permission denied to create table"

**Problem:** Using `DATABASE_URL` (app role) for migration

**Solution:**
```bash
# Use admin URL instead
psql $DATABASE_ADMIN_URL -f migrations/your_migration.sql
```

---

### Error: "DATABASE_ADMIN_URL not set"

**Problem:** Environment variable not configured

**Solution:**
```bash
# Set it temporarily
export DATABASE_ADMIN_URL=postgresql://gighala_admin:password@host:5432/gighala

# Or add to .env file permanently
echo "DATABASE_ADMIN_URL=postgresql://gighala_admin:password@host:5432/gighala" >> .env
```

---

### Error: "role gighala_admin does not exist"

**Problem:** Haven't run the role separation migration yet

**Solution:**
```bash
# First, run the role creation migration as superuser
psql $DATABASE_URL -f migrations/012_database_role_separation.sql

# Then update DATABASE_URL to use gighala_app
# And set DATABASE_ADMIN_URL to use gighala_admin
```

---

## Security Reminder

🔒 **NEVER use `DATABASE_ADMIN_URL` in production application code!**

- ✅ Use `DATABASE_ADMIN_URL` for migrations only
- ✅ Use `DATABASE_URL` (gighala_app) in your Flask app
- ❌ Don't hardcode admin credentials
- ❌ Don't commit admin credentials to git
- ❌ Don't share admin credentials publicly

---

## See Also

- `DATABASE_SECURITY_SETUP.md` - Complete setup guide
- `migrations/012_database_role_separation.sql` - Role creation migration
- `.env.example` - Environment variable template
