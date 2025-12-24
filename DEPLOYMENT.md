# GigHala Deployment Guide

## Quick Start: Fixing the Approved Budget Error

If you're seeing the error:
```
column gig.approved_budget does not exist
```

Follow these steps to rebuild and redeploy:

### 1. Rebuild the Docker Container

```bash
docker build -t gighala -f files/Dockerfile .
```

### 2. Stop the Current Container

```bash
docker stop <container-name>
docker rm <container-name>
```

### 3. Start the New Container

```bash
docker run -d \
  --name gighala \
  -p 5000:5000 \
  -e DATABASE_URL="your-database-url" \
  -e SESSION_SECRET="your-secret-key" \
  -e STRIPE_SECRET_KEY="your-stripe-key" \
  -e ALLOWED_ORIGINS="https://yourdomain.com,https://www.yourdomain.com" \
  gighala
```

**Important**: Replace `https://yourdomain.com` with your actual domain(s) in production. For local testing, the default localhost origins in the Dockerfile will be used.

### 4. Verify the Migration

Check the logs to ensure migrations ran successfully:

```bash
docker logs gighala
```

You should see output like:
```
Running database migrations...
Running approved budget migration...
✅ PostgreSQL migration completed successfully!
✅ Migration verified successfully!
Starting Gunicorn server...
```

## What Changed?

The deployment now includes:

1. **Automatic Migrations**: The `entrypoint.sh` script runs all pending migrations before starting the server
2. **Approved Budget Field**: Adds the `approved_budget` column to the `gig` table
3. **Invoice/Receipt Workflow**: Ensures invoice and receipt tables are up to date

## Manual Migration (Alternative)

If you prefer to run migrations manually inside a running container:

```bash
# Connect to the running container
docker exec -it gighala bash

# Run the approved budget migration
python migrations/run_approved_budget_migration.py

# Exit the container
exit
```

## Rollback (If Needed)

If something goes wrong, you can rollback by:

1. Stopping the new container
2. Starting the previous container version
3. Manually removing the `approved_budget` column if needed:
   ```sql
   ALTER TABLE gig DROP COLUMN IF EXISTS approved_budget;
   ```

## Required Environment Variables

The following environment variables must be set when deploying:

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `DATABASE_URL` | Yes | PostgreSQL connection string | `postgresql://user:pass@host:5432/db` |
| `SESSION_SECRET` | Yes | Secret key for session encryption | Random 32+ character string |
| `STRIPE_SECRET_KEY` | Yes | Stripe API secret key | `sk_live_...` |
| `ALLOWED_ORIGINS` | Yes* | Comma-separated list of allowed CORS origins | `https://yourdomain.com,https://www.yourdomain.com` |
| `FLASK_ENV` | No | Flask environment (`production` or `development`) | `production` (default) |
| `PORT` | No | Port to run the server on | `5000` (default) |

\* `ALLOWED_ORIGINS` has a default value of `http://localhost:5000,http://127.0.0.1:5000` which is suitable for local development only. **In production, you MUST override this** with your actual domain(s).

### ALLOWED_ORIGINS Security Note

The application enforces strict CORS policies in production mode:
- Wildcard (`*`) origins are **not allowed** in production
- You must explicitly set allowed origins as a comma-separated list
- Example: `ALLOWED_ORIGINS=https://gighala.com,https://www.gighala.com`
- The default localhost origins are only for local development/testing

## Production Deployment Notes

- Always backup your database before running migrations
- Test migrations in a staging environment first
- Monitor logs during deployment for any errors
- Verify the application works after deployment
- **Set ALLOWED_ORIGINS to your production domain(s)** - do not use the default localhost values in production
