# Migration 011: Add Email Send Log Table

**Date:** 2026-01-01
**Status:** Ready to apply

## Purpose

This migration adds the `email_send_log` table to track all email sending operations for auditing, debugging, and compliance purposes. This provides a comprehensive log of every email sent through the system, including admin bulk emails, digest emails, and transactional emails.

## What This Migration Does

1. Creates the `email_send_log` table with the following columns:
   - `id`: Primary key
   - `email_type`: Type of email (admin_bulk, admin_single, digest, transactional)
   - `subject`: Email subject line
   - `sender_user_id`: Foreign key to user table (admin who sent the email)
   - `recipient_count`: Total number of intended recipients
   - `successful_count`: Number of successfully sent emails
   - `failed_count`: Number of failed sends
   - `recipient_type`: Type of recipients (all, freelancers, clients, selected)
   - `sent_at`: Timestamp when the email send operation started
   - `success`: Boolean indicating if the overall operation succeeded
   - `error_message`: Error details if the send failed
   - `brevo_message_ids`: JSON array of Brevo message IDs for tracking
   - `failed_recipients`: JSON array of email addresses that failed

2. Adds indexes for efficient querying:
   - Index on `email_type` for filtering by email type
   - Index on `sent_at` (descending) for finding recent sends
   - Index on `success` for monitoring failed sends
   - Index on `sender_user_id` for tracking admin activity

## How to Run

### For PostgreSQL (Production):
```bash
psql $DATABASE_URL -f migrations/011_add_email_send_log.sql
```

### For SQLite (Development):
```bash
# Note: SQLite version would need AUTOINCREMENT instead of SERIAL
sqlite3 instance/gighala.db < migrations/011_add_email_send_log_sqlite.sql
```

### Via Python Migration Runner:
```python
from app import app, db

with app.app_context():
    # Read and execute the migration file
    with open('migrations/011_add_email_send_log.sql', 'r') as f:
        migration_sql = f.read()
    db.session.execute(migration_sql)
    db.session.commit()
    print("Migration 011 applied successfully!")
```

## Verification

After running the migration, verify the table exists:

### PostgreSQL:
```sql
\d email_send_log
SELECT * FROM email_send_log LIMIT 5;
```

### SQLite:
```sql
.schema email_send_log
SELECT * FROM email_send_log LIMIT 5;
```

## Rollback

To rollback this migration (if needed):

```sql
DROP TABLE IF EXISTS email_send_log;
```

## Related Changes

This migration is part of the email logging feature, which includes:
- New `EmailSendLog` model in `app.py`
- Enhanced logging in `email_service.py`
- Database logging in admin email endpoints
- Integration with Brevo email service

## Benefits

- **Auditing**: Track who sent what emails and when
- **Debugging**: Identify patterns in failed email sends
- **Compliance**: Maintain records of all email communications
- **Monitoring**: Track email service health and success rates
- **Analytics**: Analyze email sending patterns and effectiveness

## Notes

- The table is designed to work with PostgreSQL (production) and SQLite (development)
- Each email send operation creates one log entry with aggregate statistics
- The `sent_at` timestamp uses UTC
- Failed sends are logged with `success=False` and include error details
- JSON fields (`brevo_message_ids`, `failed_recipients`) store arrays as text
- The sender relationship allows tracking which admin sent each email
