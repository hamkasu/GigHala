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
  gighala
```

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

## Production Deployment Notes

- Always backup your database before running migrations
- Test migrations in a staging environment first
- Monitor logs during deployment for any errors
- Verify the application works after deployment
