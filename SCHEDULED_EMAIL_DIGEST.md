# Scheduled Email Digest Feature

## Overview

GigHala now sends automated email digests to users about new gigs posted on the platform. Emails are sent twice daily at:
- **8:00 AM** (Malaysia time)
- **8:00 PM** (Malaysia time)

## Features

- Sends personalized emails to all users who have opted in
- Includes all new gigs posted since the last digest
- Supports both English and Malay (based on user language preference)
- Respects user notification preferences
- Tracks all sent digests in the database
- Handles errors gracefully with logging

## Components

### 1. Email Template
**File:** `templates/email_new_gigs_digest.html`

Beautiful, responsive HTML email template that includes:
- User's name in greeting
- Count of new gigs
- Gig details (title, category, budget, location, description)
- Direct links to view gigs and apply
- Halal compliance indicators
- Remote work indicators
- User preference management link

### 2. Scheduled Jobs Module
**File:** `scheduled_jobs.py`

Contains:
- `send_new_gigs_digest()`: Main function that queries new gigs and sends emails
- `init_scheduler()`: Initializes APScheduler with cron triggers
- Logging for monitoring and debugging

### 3. Database Model
**File:** `app.py` (EmailDigestLog model)

Tracks each digest send with:
- Digest type (e.g., 'new_gigs')
- Timestamp when sent
- Number of recipients
- Number of gigs included
- Success/failure status
- Error messages (if failed)

### 4. Database Migration
**Files:**
- `migrations/010_add_email_digest_log.sql` (PostgreSQL)
- `migrations/010_add_email_digest_log_sqlite.sql` (SQLite)

Creates the `email_digest_log` table and indexes.

## Setup Instructions

### 1. Install Dependencies

The feature requires APScheduler, which is already added to `requirements.txt`:

```bash
pip install -r requirements.txt
```

### 2. Run Database Migration

**PostgreSQL:**
```bash
psql $DATABASE_URL -f migrations/010_add_email_digest_log.sql
```

**SQLite (development):**
```bash
sqlite3 instance/gighala.db < migrations/010_add_email_digest_log_sqlite.sql
```

### 3. Configure Environment Variables

Add to your `.env` file:

```bash
# Required for sending emails
SENDGRID_API_KEY=your-sendgrid-api-key
SENDGRID_FROM_EMAIL=noreply@gighala.my

# Application URL (for links in emails)
BASE_URL=https://gighala.my

# Timezone for scheduled jobs (default: Asia/Kuala_Lumpur)
TIMEZONE=Asia/Kuala_Lumpur
```

### 4. Start the Application

The scheduler starts automatically when the Flask app starts:

```bash
python app.py
```

You should see in the logs:
```
Scheduler started with timezone: Asia/Kuala_Lumpur
Scheduled jobs:
  - New gigs email digest at 8:00 AM
  - New gigs email digest at 8:00 PM
```

## Testing

### Manual Testing

Run the test script to manually trigger a digest:

```bash
python test_email_digest.py
```

This will:
1. Trigger the digest function immediately
2. Display the results
3. Show recent digest logs from the database

### View Digest Logs

In PostgreSQL:
```sql
SELECT * FROM email_digest_log ORDER BY sent_at DESC LIMIT 10;
```

In SQLite:
```sql
SELECT * FROM email_digest_log ORDER BY sent_at DESC LIMIT 10;
```

## How It Works

### 1. Scheduled Execution

APScheduler runs the digest job at 8 AM and 8 PM Malaysia time:
- Uses cron triggers for precise scheduling
- Runs in a background thread
- Automatically starts with the Flask app

### 2. Digest Generation

When the job runs:
1. Queries `email_digest_log` to find the last send time
2. Queries `gig` table for gigs created since last send (or last 12 hours if no previous send)
3. Filters gigs to only include those with status='open'
4. Queries all users with email addresses

### 3. User Filtering

Emails are sent to users who:
- Have a valid email address
- Have `email_new_gig` preference set to `True` in `notification_preference` table
- OR have no notification preferences set (defaults to True)

### 4. Email Personalization

Each email includes:
- User's name (from `full_name`, `username`, or "User")
- Subject line in user's preferred language (English or Malay)
- List of all new gigs with details
- Links to view each gig and apply

### 5. Sending & Logging

- Uses existing `EmailService` class with SendGrid
- Sends emails individually (no BCC) for privacy
- Logs the send attempt to `email_digest_log` table
- Records success/failure and error messages

## User Notification Preferences

Users can control whether they receive new gig emails:

1. Go to Settings → Notifications
2. Toggle "Email notifications for new gigs"
3. Changes are saved to the `notification_preference` table

Default: **Enabled** (users receive emails unless they opt out)

## Monitoring

### Check Scheduler Status

The scheduler logs information on startup. Check your application logs for:
```
Scheduler started with timezone: Asia/Kuala_Lumpur
```

### Monitor Digest Sends

Query the `email_digest_log` table:
```sql
SELECT
    digest_type,
    sent_at,
    recipient_count,
    gig_count,
    success,
    error_message
FROM email_digest_log
ORDER BY sent_at DESC
LIMIT 20;
```

### Check for Failures

Find failed digest attempts:
```sql
SELECT * FROM email_digest_log
WHERE success = FALSE
ORDER BY sent_at DESC;
```

## Troubleshooting

### Emails Not Sending

1. **Check SendGrid API Key:**
   ```bash
   echo $SENDGRID_API_KEY
   ```
   Verify it's set and valid

2. **Check Logs:**
   Look for error messages in application logs

3. **Verify Email Service:**
   Test SendGrid separately:
   ```python
   from email_service import email_service
   result = email_service.send_single_email(
       to='test@example.com',
       subject='Test',
       html='<p>Test email</p>'
   )
   print(result)
   ```

4. **Check Digest Logs:**
   See if digests are being logged with errors:
   ```sql
   SELECT * FROM email_digest_log WHERE success = FALSE;
   ```

### Scheduler Not Running

1. **Verify APScheduler Installation:**
   ```bash
   pip list | grep APScheduler
   ```

2. **Check Timezone:**
   Ensure `TIMEZONE` environment variable is set correctly

3. **Check Logs:**
   Look for "Scheduler started" message in logs

4. **Manual Trigger:**
   Use the test script to verify the function works:
   ```bash
   python test_email_digest.py
   ```

### No New Gigs in Digest

This is expected if:
- No new gigs were posted since the last digest
- All new gigs have status other than 'open'

Users will still receive an email saying "No new gigs posted."

## Customization

### Change Schedule Times

Edit `scheduled_jobs.py`:

```python
# Change morning time (currently 8 AM)
scheduler.add_job(
    func=...,
    trigger=CronTrigger(hour=9, minute=0, timezone=timezone),  # Change to 9 AM
    ...
)

# Change evening time (currently 8 PM)
scheduler.add_job(
    func=...,
    trigger=CronTrigger(hour=21, minute=30, timezone=timezone),  # Change to 9:30 PM
    ...
)
```

### Modify Email Template

Edit `templates/email_new_gigs_digest.html` to customize:
- Layout and styling
- Content and wording
- Colors and branding
- Additional information to include

### Add More Digest Types

Create new digest functions in `scheduled_jobs.py`:

```python
def send_weekly_summary(app, db, ...):
    # Your weekly summary logic
    pass

# Schedule it
scheduler.add_job(
    func=lambda: send_weekly_summary(...),
    trigger=CronTrigger(day_of_week='mon', hour=8, minute=0),
    id='weekly_summary',
    name='Send weekly summary'
)
```

## Production Deployment

### Railway / Heroku

The scheduler works automatically with:
- Gunicorn (current setup)
- The scheduler runs in a background thread
- No additional worker process needed

### Important Notes

1. **Single Instance:** If running multiple app instances, the scheduler will run in each instance. Consider using a distributed task queue (Celery) for production at scale.

2. **Timezone:** Ensure server timezone or `TIMEZONE` env var is set correctly

3. **Monitoring:** Set up alerts for failed digests:
   ```sql
   SELECT COUNT(*) FROM email_digest_log
   WHERE success = FALSE
   AND sent_at > NOW() - INTERVAL '24 hours';
   ```

4. **Email Limits:** Monitor SendGrid usage to stay within your plan limits

## Future Enhancements

Potential improvements:
- [ ] Add digest preview in admin panel
- [ ] Allow users to choose digest frequency (daily, twice daily, weekly)
- [ ] Add category-based filtering (users only get gigs in their skill categories)
- [ ] Include trending gigs or featured gigs
- [ ] Add unsubscribe link directly in email
- [ ] Send test emails from admin panel
- [ ] Add email open tracking
- [ ] A/B test different email templates

## Support

For issues or questions:
1. Check the logs in `email_digest_log` table
2. Run the test script: `python test_email_digest.py`
3. Review error messages in application logs
4. Contact the development team with digest log IDs

## License

This feature is part of the GigHala platform and follows the same license as the main application.
