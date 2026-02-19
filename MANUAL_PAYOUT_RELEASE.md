# Manual Payout Release System

## Overview

The Manual Payout Release system allows admins to process payout withdrawals in scheduled batches at **8:00 AM** and **4:00 PM** daily (Malaysia Time). This provides controlled, predictable payout processing and allows admins to release payments through their external banking app while tracking the status within GigHala.

## Key Features

- **Scheduled Batches**: All payout requests are automatically assigned to the next available batch (8am or 4pm)
- **Two-Step Workflow**: Admins first mark payouts as "ready for release", then confirm after making the payment
- **Batch View**: Visual grouping of payouts by scheduled release time
- **Complete Audit Trail**: All actions are logged with timestamps and admin identifiers
- **Email Notifications**: Users receive email confirmation when their payout is completed

## How It Works

### For Users (Freelancers)

1. **Request Payout**: User requests a payout from their wallet balance
2. **Automatic Batching**: System automatically assigns the payout to the next scheduled batch:
   - If before 8am → assigned to today's 8am batch
   - If between 8am and 4pm → assigned to today's 4pm batch
   - If after 4pm → assigned to tomorrow's 8am batch
3. **Wait for Release**: Payout enters "pending" status and funds are held in wallet
4. **Receive Confirmation**: User receives email when admin confirms the payment has been released

### For Admins

1. **View Batches**: Switch to "Batch View" in the Admin Dashboard → Payouts tab
2. **Mark Ready for Release**: Review payouts and click "Mark Ready" to prepare them for payment
3. **Process Payments**: Make bank transfers through your external banking app
4. **Confirm Payment**: Click "Confirm Payment" in GigHala to complete the payout and notify the user

## User Interface

### Batch View

The Batch View groups payouts by their scheduled release time:

- **Batch Header**: Shows scheduled time (8am or 4pm), total amount, payout count, and progress
- **Color Coding**:
  - White background: Pending (not yet marked ready)
  - Yellow background: Ready for Release (marked by admin, awaiting payment)
  - Green background: Payment Confirmed (payment released and confirmed)
- **Action Buttons**:
  - "Mark Ready": Moves payout to ready-for-release status
  - "Confirm Payment": Confirms external payment has been made
  - "Details": View full payout details and bank account information

### List View

Traditional table view with all payouts sorted by date. Use the status filter to show:
- Pending
- Processing (ready for release)
- Completed (payment confirmed)
- Failed
- Cancelled

## Database Schema

New fields added to the `payout` table:

| Field | Type | Description |
|-------|------|-------------|
| `scheduled_release_time` | TIMESTAMP | Scheduled batch release time (8am or 4pm UTC) |
| `release_batch` | VARCHAR(50) | Batch identifier (e.g., "2026-01-12-08:00") |
| `ready_for_release` | BOOLEAN | Admin marked ready for batch release |
| `ready_for_release_at` | TIMESTAMP | When admin marked it ready |
| `ready_for_release_by` | INTEGER | User ID of admin who marked it ready |
| `external_payment_confirmed` | BOOLEAN | Admin confirmed external payment done |
| `external_payment_confirmed_at` | TIMESTAMP | When admin confirmed payment |
| `external_payment_confirmed_by` | INTEGER | User ID of admin who confirmed payment |

## API Endpoints

### Get Payout Batches
```
GET /api/admin/billing/payouts/batches
Authorization: Admin required
```

Returns all pending and processing payouts grouped by release batch.

**Response:**
```json
{
  "batches": [
    {
      "batch_id": "2026-01-12-08:00",
      "scheduled_time": "2026-01-12 08:00:00",
      "total_amount": 5000.00,
      "total_net_amount": 4900.00,
      "payout_count": 10,
      "ready_count": 5,
      "confirmed_count": 3,
      "payouts": [...]
    }
  ],
  "total_batches": 2
}
```

### Mark Payout Ready
```
PUT /api/admin/billing/payouts/<payout_id>/mark-ready
Authorization: Admin required
```

Marks a payout as ready for batch release.

**Response:**
```json
{
  "message": "Payout marked as ready for release"
}
```

### Confirm Payment
```
PUT /api/admin/billing/payouts/<payout_id>/confirm-payment
Authorization: Admin required
Content-Type: application/json
```

Confirms that external payment has been released through banking app.

**Request Body:**
```json
{
  "admin_notes": "Payment released via Maybank (optional)"
}
```

**Response:**
```json
{
  "message": "Payment confirmed and payout completed"
}
```

**Side Effects:**
- Updates payout status to "completed"
- Releases held balance from user's wallet
- Creates payment history record
- Sends email notification to user
- Sends SMS notification (for amounts >= RM 500)
- Logs financial transaction for audit

## Security & Audit Logging

All manual payout release actions are logged with:

- Event type: `payout_confirmed`
- Admin username and ID
- Payout details (amount, freelancer, batch)
- Timestamp
- Admin notes
- Security severity level

View logs in the Admin Dashboard → Security Logs section.

## Installation & Setup

### 1. Run Database Migration

```bash
# Automatic migration (detects database type)
python3 migrations/run_manual_payout_batch_migration.py

# Or manually apply SQL
# For PostgreSQL:
psql -U your_user -d your_database -f migrations/015_add_manual_payout_batch_release.sql

# For SQLite:
sqlite3 your_database.db < migrations/015_add_manual_payout_batch_release_sqlite.sql
```

### 2. Verify Migration

The migration script will verify all columns are created correctly.

### 3. Access Admin Dashboard

1. Log in as an admin user
2. Navigate to Admin Dashboard → Payouts
3. Click "📦 Batch View" to see the new interface

## Workflow Example

### Example: Processing the 8am Batch

**7:30 AM - User Requests Payout**
- User requests RM 1,000 payout
- System assigns to today's 8am batch (ID: "2026-01-12-08:00")
- Funds held in wallet, status: "pending"

**7:45 AM - Admin Reviews Batch**
- Admin clicks "Batch View" in dashboard
- Sees 8am batch with 15 payouts totaling RM 15,000
- Reviews each payout's bank details
- Clicks "Mark Ready" on verified payouts

**8:00 AM - Admin Processes Payments**
- Opens Maybank/CIMB banking app
- Makes 15 individual transfers based on GigHala batch list
- Verifies each transfer completes successfully

**8:15 AM - Admin Confirms in GigHala**
- Returns to GigHala Batch View
- Clicks "Confirm Payment" for each completed transfer
- Adds optional note: "Transferred via Maybank at 8:10 AM"
- System sends email/SMS to each user
- Batch status updates show 15/15 confirmed

**8:20 AM - Users Receive Notifications**
- Users receive email: "Withdrawal Completed - PO-20260112-12345"
- SMS sent for large withdrawals (>= RM 500)
- Payment history updated in user wallets

## Timezone Handling

- **User Display**: Malaysia Time (MYT = UTC+8)
- **Database Storage**: UTC timestamps
- **Batch Calculation**: Uses Malaysia timezone to determine 8am/4pm cutoffs
- **Frontend**: Automatically converts UTC to local time for display

## Best Practices

### For Admins

1. **Review Before Marking Ready**: Verify bank account details before marking payouts ready
2. **Process Promptly**: Try to process batches at scheduled times (8am/4pm)
3. **Add Notes**: Include banking app name and timestamp in confirmation notes
4. **Verify Transfers**: Double-check transfer amounts match payout net amounts
5. **Monitor Progress**: Use batch progress indicators to track completion

### For System Administrators

1. **Backup Before Migration**: Always backup database before running migration
2. **Test on Staging**: Test batch workflow on staging environment first
3. **Monitor Logs**: Review security logs for unusual payout patterns
4. **Set Alerts**: Configure alerts for large batches (e.g., >RM 50,000)
5. **Regular Audits**: Reconcile GigHala records with bank statements weekly

## Troubleshooting

### Payout Not Showing in Batch

**Cause**: Payout may be instant payout (Stripe Connect) or already completed

**Solution**: Check the List View with "All Status" filter

### Cannot Mark Payout Ready

**Cause**: Payout status must be "pending" or "processing"

**Solution**: Check payout status in Details view. If "completed" or "failed", it cannot be marked ready.

### Confirmed Payment Not Releasing Balance

**Cause**: Payout must be marked "ready for release" first

**Solution**: Follow two-step workflow: Mark Ready → Confirm Payment

### Timezone Confusion

**Cause**: Database stores UTC, display shows MYT

**Solution**: All batch times are Malaysia Time (MYT). Check scheduled_release_time field for UTC equivalent.

## Migration Rollback

If you need to rollback this feature:

```sql
-- PostgreSQL
ALTER TABLE payout DROP COLUMN IF EXISTS scheduled_release_time;
ALTER TABLE payout DROP COLUMN IF EXISTS release_batch;
ALTER TABLE payout DROP COLUMN IF EXISTS ready_for_release;
ALTER TABLE payout DROP COLUMN IF EXISTS ready_for_release_at;
ALTER TABLE payout DROP COLUMN IF EXISTS ready_for_release_by;
ALTER TABLE payout DROP COLUMN IF EXISTS external_payment_confirmed;
ALTER TABLE payout DROP COLUMN IF EXISTS external_payment_confirmed_at;
ALTER TABLE payout DROP COLUMN IF EXISTS external_payment_confirmed_by;

DROP INDEX IF EXISTS idx_payout_release_batch;
DROP INDEX IF EXISTS idx_payout_scheduled_release_time;
DROP INDEX IF EXISTS idx_payout_ready_for_release;
DROP INDEX IF EXISTS idx_payout_external_payment_confirmed;
```

## Support

For issues or questions:
- Check Security Logs: Admin Dashboard → Security Logs
- Review Database: Check `payout` table for batch assignments
- Contact Support: support@gighala.my

## Version History

- **v1.0 (2026-01-12)**: Initial release
  - Scheduled batch processing (8am/4pm)
  - Two-step approval workflow
  - Batch view interface
  - Security logging
  - Email/SMS notifications
