# Commission Tracking Migration

## Overview
This migration fixes the commission tracking issue where released escrows were not creating Transaction records, causing the admin financial statistics to show RM 0.00 for commission even though payouts were being made.

## Problem
The platform had two different flows for completing gigs:
1. **Billing flow** (`/api/billing/complete-gig/<gig_id>`) - Creates Transaction records with commission ✓
2. **Escrow flow** (`/api/escrow/<gig_id>/release`) - Did NOT create Transaction records ✗

This caused a discrepancy where:
- Total Payout: RM 1600.00 (from released escrows)
- Commission: RM 0.00 (from transaction records)

## Changes Made

### Code Fixes (app.py)
1. **Escrow Release Endpoint** (line ~3978)
   - Now creates/updates Transaction records when escrow is released
   - Tracks commission from escrow.platform_fee

2. **Milestone Approval** (line ~8886)
   - Creates Transaction record when all milestones are completed
   - Ensures commission is tracked for milestone-based payments

3. **Dispute Resolution** (line ~8669)
   - Creates Transaction record when payment is released via dispute resolution
   - Maintains commission tracking across all payment flows

### Data Migration Script
**File:** `003_backfill_commission_transactions.py`

This script backfills Transaction records for existing released escrows.

## Running the Migration

### Option 1: Using Docker (Recommended)
```bash
# If using docker-compose
docker-compose exec web python3 migrations/003_backfill_commission_transactions.py

# If using docker run
docker exec -it <container_name> python3 migrations/003_backfill_commission_transactions.py
```

### Option 2: Direct Python (if Flask environment is set up)
```bash
cd /path/to/GigHala
python3 migrations/003_backfill_commission_transactions.py
```

### Option 3: Using Flask Shell
```bash
flask shell
>>> exec(open('migrations/003_backfill_commission_transactions.py').read())
```

## What the Migration Does
1. Finds all escrows with status='released'
2. For each released escrow:
   - Checks if a Transaction record exists for that gig
   - If not, creates a new Transaction with:
     - commission = escrow.platform_fee
     - status = 'completed'
     - All other relevant escrow details
   - If Transaction exists but commission is 0 or NULL, updates it
3. Reports summary of:
   - Total released escrows processed
   - New transactions created
   - Existing transactions updated
   - Total commission now tracked

## Expected Results
After running the migration, the admin financial statistics should show:
- **Total Payout**: Sum of all released escrow amounts
- **Commission**: Sum of all transaction commissions (previously RM 0.00, now correctly calculated)
- **Escrow**: Sum of all currently funded escrows

## Verification
To verify the migration worked correctly:

```sql
-- Check total commission from completed transactions
SELECT SUM(commission) as total_commission
FROM transaction
WHERE status = 'completed';

-- Check released escrows vs transactions
SELECT
    (SELECT COUNT(*) FROM escrow WHERE status = 'released') as released_escrows,
    (SELECT COUNT(*) FROM transaction WHERE status = 'completed') as completed_transactions;

-- View commission by gig
SELECT
    t.gig_id,
    e.escrow_number,
    e.amount,
    e.platform_fee,
    t.commission,
    t.status
FROM transaction t
JOIN escrow e ON t.gig_id = e.gig_id
WHERE e.status = 'released'
ORDER BY t.transaction_date DESC;
```

## Rollback (if needed)
If you need to rollback this migration:

```sql
-- Remove transactions created by this migration
-- Only do this if you're certain these transactions should not exist
DELETE FROM transaction
WHERE payment_method = 'escrow'
AND transaction_date >= 'YYYY-MM-DD';  -- Use migration run date
```

## Notes
- This is a one-time data migration to fix historical data
- All new escrow releases will automatically create Transaction records
- The migration is idempotent - safe to run multiple times
- Existing transactions with commission are skipped (not modified)
