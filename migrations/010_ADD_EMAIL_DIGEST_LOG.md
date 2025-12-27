# Migration 010: Add Email Digest Log Table

**Date:** 2025-12-27
**Status:** Ready to apply

## Purpose

This migration adds the `email_digest_log` table to track scheduled email digests sent to users. This supports the new scheduled email notification feature that sends digest emails about new gigs twice daily (8 AM and 8 PM).

## What This Migration Does

1. Creates the `email_digest_log` table with the following columns:
   - `id`: Primary key
   - `digest_type`: Type of digest (e.g., 'new_gigs', 'weekly_summary')
   - `sent_at`: Timestamp when the digest was sent
   - `recipient_count`: Number of users who received the email
   - `gig_count`: Number of gigs included in the digest
   - `success`: Whether the send operation succeeded
   - `error_message`: Error details if the send failed

2. Adds indexes for efficient querying:
   - Index on `digest_type` for filtering by digest type
   - Index on `sent_at` (descending) for finding recent digests
   - Index on `success` for monitoring failed sends

## How to Run

### For PostgreSQL (Production):
```bash
psql $DATABASE_URL -f migrations/010_add_email_digest_log.sql
```

### For SQLite (Development):
```bash
sqlite3 instance/gighala.db < migrations/010_add_email_digest_log_sqlite.sql
```

### Via Python Migration Runner:
```python
from app import app, db

with app.app_context():
    # Read and execute the migration file
    with open('migrations/010_add_email_digest_log.sql', 'r') as f:
        migration_sql = f.read()
    db.session.execute(migration_sql)
    db.session.commit()
    print("Migration 010 applied successfully!")
```

## Verification

After running the migration, verify the table exists:

### PostgreSQL:
```sql
\d email_digest_log
SELECT * FROM email_digest_log LIMIT 5;
```

### SQLite:
```sql
.schema email_digest_log
SELECT * FROM email_digest_log LIMIT 5;
```

## Rollback

To rollback this migration (if needed):

```sql
DROP TABLE IF EXISTS email_digest_log;
```

## Related Changes

This migration is part of the scheduled email notifications feature, which includes:
- New `EmailDigestLog` model in `app.py`
- Scheduled job functions in `scheduled_jobs.py`
- Email template: `templates/email_new_gigs_digest.html`
- APScheduler integration in `app.py`

## Notes

- The table is designed to work with both PostgreSQL and SQLite
- Each digest send creates one log entry
- The `sent_at` timestamp uses UTC
- Failed sends are logged with `success=False` and include an error message
- This table helps monitor the health of the scheduled email system
