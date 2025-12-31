-- Test Cancellation System Using EXISTING Database Data
-- Use these queries to test without creating new records

-- ============================================================================
-- STEP 1: Find existing gigs that can be cancelled
-- ============================================================================

-- Find OPEN gigs (easiest to cancel - no refunds needed)
SELECT
    g.id,
    g.gig_code,
    g.title,
    g.status,
    u.username as client,
    g.budget_min,
    g.budget_max,
    (SELECT COUNT(*) FROM application WHERE gig_id = g.id AND status = 'pending') as pending_apps
FROM gig g
JOIN "user" u ON g.client_id = u.id
WHERE g.status = 'open'
    AND g.cancellation_reason IS NULL
ORDER BY g.created_at DESC
LIMIT 10;

-- Find IN_PROGRESS gigs (will test refund logic)
SELECT
    g.id,
    g.gig_code,
    g.title,
    g.status,
    client.username as client,
    freelancer.username as freelancer,
    g.agreed_amount,
    e.escrow_number,
    e.status as escrow_status,
    e.amount as escrow_amount
FROM gig g
JOIN "user" client ON g.client_id = client.id
LEFT JOIN "user" freelancer ON g.freelancer_id = freelancer.id
LEFT JOIN escrow e ON e.gig_id = g.id
WHERE g.status = 'in_progress'
    AND g.cancellation_reason IS NULL
ORDER BY g.created_at DESC
LIMIT 10;

-- ============================================================================
-- STEP 2: Get user IDs for testing
-- ============================================================================

-- Find clients
SELECT id, username, email, is_client
FROM "user"
WHERE is_client = TRUE
ORDER BY created_at DESC
LIMIT 5;

-- Find freelancers
SELECT id, username, email, is_freelancer
FROM "user"
WHERE is_freelancer = TRUE
ORDER BY created_at DESC
LIMIT 5;

-- ============================================================================
-- STEP 3: Manual cancellation using existing gig ID
-- ============================================================================

-- Replace <GIG_ID> with an actual gig ID from STEP 1 queries above

-- Example: Cancel gig with ID 5
UPDATE gig
SET
    status = 'cancelled',
    cancellation_reason = 'Testing cancellation system - manual SQL test',
    cancelled_at = NOW()
WHERE id = 5  -- REPLACE WITH ACTUAL GIG ID
    AND status != 'completed'  -- Safety check
    AND status != 'cancelled'  -- Don't cancel twice
RETURNING id, gig_code, title, status, cancellation_reason;


-- ============================================================================
-- STEP 4: Manually process refund for cancelled gig with escrow
-- ============================================================================

-- Replace <GIG_ID> with the ID of an in_progress gig that has escrow

-- Get escrow details first
SELECT
    e.id as escrow_id,
    e.gig_id,
    e.amount,
    e.status,
    e.client_id,
    w.balance as client_current_balance,
    w.held_balance as client_held_balance
FROM escrow e
JOIN wallet w ON e.client_id = w.user_id
WHERE e.gig_id = 5;  -- REPLACE WITH ACTUAL GIG ID

-- Process the refund
BEGIN;

-- 1. Update escrow status
UPDATE escrow
SET
    status = 'refunded',
    refunded_amount = amount,
    refunded_at = NOW(),
    admin_notes = COALESCE(admin_notes || E'\n', '') || 'Manual cancellation refund - testing'
WHERE gig_id = 5  -- REPLACE WITH ACTUAL GIG ID
    AND status = 'funded'
RETURNING escrow_number, amount as refunded_amount;

-- 2. Update client wallet (release held balance, add back to available balance)
UPDATE wallet
SET
    held_balance = held_balance - (
        SELECT amount FROM escrow WHERE gig_id = 5  -- REPLACE WITH ACTUAL GIG ID
    ),
    balance = balance + (
        SELECT amount FROM escrow WHERE gig_id = 5  -- REPLACE WITH ACTUAL GIG ID
    )
WHERE user_id = (
    SELECT client_id FROM gig WHERE id = 5  -- REPLACE WITH ACTUAL GIG ID
)
RETURNING user_id, balance, held_balance;

-- 3. Create payment history record
INSERT INTO payment_history (
    user_id,
    type,
    amount,
    balance_before,
    balance_after,
    description,
    status,
    created_at
)
SELECT
    g.client_id,
    'refund',
    e.amount,
    w.balance - e.amount,  -- balance before
    w.balance,             -- balance after
    'Refund for cancelled gig: ' || g.title,
    'completed',
    NOW()
FROM gig g
JOIN escrow e ON e.gig_id = g.id
JOIN wallet w ON w.user_id = g.client_id
WHERE g.id = 5  -- REPLACE WITH ACTUAL GIG ID
RETURNING id, user_id, type, amount, description;

COMMIT;


-- ============================================================================
-- STEP 5: Verify the cancellation worked correctly
-- ============================================================================

-- Check gig status
SELECT
    id,
    gig_code,
    title,
    status,
    cancellation_reason,
    cancelled_at
FROM gig
WHERE id = 5;  -- REPLACE WITH ACTUAL GIG ID

-- Check escrow was refunded
SELECT
    escrow_number,
    amount,
    status,
    refunded_amount,
    refunded_at
FROM escrow
WHERE gig_id = 5;  -- REPLACE WITH ACTUAL GIG ID

-- Check wallet was updated
SELECT
    u.username,
    w.balance,
    w.held_balance
FROM wallet w
JOIN "user" u ON w.user_id = u.id
WHERE u.id = (SELECT client_id FROM gig WHERE id = 5);  -- REPLACE WITH ACTUAL GIG ID

-- Check payment history was created
SELECT
    type,
    amount,
    description,
    status,
    created_at
FROM payment_history
WHERE user_id = (SELECT client_id FROM gig WHERE id = 5)  -- REPLACE WITH ACTUAL GIG ID
ORDER BY created_at DESC
LIMIT 5;


-- ============================================================================
-- STEP 6: Check notifications were sent
-- ============================================================================

-- Check notifications for the cancelled gig
SELECT
    n.notification_type,
    n.title,
    n.message,
    u.username as recipient,
    n.created_at,
    n.is_read
FROM notification n
JOIN "user" u ON n.user_id = u.id
WHERE n.related_id = 5  -- REPLACE WITH ACTUAL GIG ID
ORDER BY n.created_at DESC;


-- ============================================================================
-- QUICK STATS: Cancelled Gigs Summary
-- ============================================================================

-- Count cancelled gigs by reason
SELECT
    LEFT(cancellation_reason, 50) as reason_preview,
    COUNT(*) as count,
    SUM(agreed_amount) as total_amount_cancelled
FROM gig
WHERE status = 'cancelled'
    AND cancelled_at IS NOT NULL
GROUP BY LEFT(cancellation_reason, 50)
ORDER BY count DESC;

-- Recent cancellations
SELECT
    g.gig_code,
    g.title,
    g.status,
    client.username as client,
    COALESCE(freelancer.username, 'No freelancer') as freelancer,
    g.agreed_amount,
    g.cancelled_at,
    LEFT(g.cancellation_reason, 60) as reason
FROM gig g
JOIN "user" client ON g.client_id = client.id
LEFT JOIN "user" freelancer ON g.freelancer_id = freelancer.id
WHERE g.status = 'cancelled'
ORDER BY g.cancelled_at DESC
LIMIT 20;

-- Refunds processed
SELECT
    e.escrow_number,
    g.gig_code,
    e.amount as original_amount,
    e.refunded_amount,
    e.status,
    e.refunded_at,
    client.username as refunded_to
FROM escrow e
JOIN gig g ON e.gig_id = g.id
JOIN "user" client ON e.client_id = client.id
WHERE e.status = 'refunded'
ORDER BY e.refunded_at DESC
LIMIT 20;


-- ============================================================================
-- ROLLBACK: Undo a test cancellation
-- ============================================================================

-- WARNING: Only use this if you need to undo a test cancellation
-- Replace <GIG_ID> with the gig you want to restore

/*
BEGIN;

-- Restore gig status
UPDATE gig
SET
    status = 'in_progress',  -- Or 'open' depending on what it was
    cancellation_reason = NULL,
    cancelled_at = NULL
WHERE id = 5;  -- REPLACE WITH ACTUAL GIG ID

-- Restore escrow
UPDATE escrow
SET
    status = 'funded',
    refunded_amount = 0,
    refunded_at = NULL
WHERE gig_id = 5;  -- REPLACE WITH ACTUAL GIG ID

-- Restore wallet (reverse the refund)
UPDATE wallet
SET
    held_balance = held_balance + (
        SELECT amount FROM escrow WHERE gig_id = 5
    ),
    balance = balance - (
        SELECT amount FROM escrow WHERE gig_id = 5
    )
WHERE user_id = (
    SELECT client_id FROM gig WHERE id = 5
);

-- Delete the refund payment history
DELETE FROM payment_history
WHERE user_id = (SELECT client_id FROM gig WHERE id = 5)
    AND type = 'refund'
    AND created_at > NOW() - INTERVAL '1 hour'  -- Only recent ones
    AND description LIKE '%cancelled gig%';

COMMIT;
*/
