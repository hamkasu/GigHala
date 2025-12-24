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
  -e FLASK_ENV="production" \
  -e DATABASE_URL="your-database-url" \
  -e SESSION_SECRET="your-secret-key" \
  -e STRIPE_SECRET_KEY="your-stripe-key" \
  -e ALLOWED_ORIGINS="https://yourdomain.com,https://www.yourdomain.com" \
  gighala
```

**Important**:
- Replace `https://yourdomain.com` with your actual domain(s) in production
- Set `FLASK_ENV=production` for production deployments
- For local testing, the container defaults to development mode with localhost origins

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

| Variable | Required | Description | Default | Example |
|----------|----------|-------------|---------|---------|
| `DATABASE_URL` | Yes | PostgreSQL connection string | None | `postgresql://user:pass@host:5432/db` |
| `SESSION_SECRET` | Yes | Secret key for session encryption | None | Random 32+ character string |
| `STRIPE_SECRET_KEY` | Yes | Stripe API secret key | None | `sk_live_...` |
| `FLASK_ENV` | **Production** | Flask environment | `development` | `production` |
| `ALLOWED_ORIGINS` | **Production** | Comma-separated list of allowed CORS origins | localhost URLs | `https://yourdomain.com,https://www.yourdomain.com` |
| `PORT` | No | Port to run the server on | `5000` | `8080` |

**Development Mode Defaults:**
- `FLASK_ENV`: `development` (allows wildcard CORS for easier local development)
- `ALLOWED_ORIGINS`: `http://localhost:5000,http://127.0.0.1:5000,https://localhost:5000,https://127.0.0.1:5000`

**Production Requirements:**
- Set `FLASK_ENV=production` to enable production mode
- Set `ALLOWED_ORIGINS` to your actual domain(s) - never use wildcards in production

### ALLOWED_ORIGINS Security Note

The application enforces strict CORS policies based on the `FLASK_ENV` setting:

**Development Mode** (`FLASK_ENV=development` - default):
- Allows wildcard (`*`) origins if `ALLOWED_ORIGINS` is not set
- Default localhost origins are pre-configured for convenience
- This mode is intended for local development only

**Production Mode** (`FLASK_ENV=production`):
- Wildcard (`*`) origins are **strictly prohibited**
- `ALLOWED_ORIGINS` must be explicitly set to a comma-separated list of your actual domains
- The application will refuse to start if ALLOWED_ORIGINS is not properly configured
- Example: `ALLOWED_ORIGINS=https://gighala.com,https://www.gighala.com`

## Production Deployment Notes

- Always backup your database before running migrations
- Test migrations in a staging environment first
- Monitor logs during deployment for any errors
- Verify the application works after deployment
- **Set `FLASK_ENV=production`** to enable production security checks
- **Set `ALLOWED_ORIGINS` to your actual production domain(s)** - do not rely on defaults in production
- Never use `FLASK_DEBUG=True` in production environments
