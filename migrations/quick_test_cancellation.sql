-- QUICK TEST: Simple Insert Queries for Cancellation Testing
-- These queries use simple sequential IDs - adjust as needed for your database

-- ============================================================================
-- SCENARIO 1: Cancel an OPEN gig (no escrow, no freelancer assigned)
-- ============================================================================

-- Insert test client
INSERT INTO "user" (username, email, password_hash, is_client, is_freelancer, is_verified, created_at)
VALUES ('cancel_test_client1', 'cancelclient1@test.com', 'pbkdf2:sha256:260000$test$test', TRUE, FALSE, TRUE, NOW());
-- Assume this creates user ID = 100

-- Insert client wallet
INSERT INTO wallet (user_id, balance, held_balance, created_at)
VALUES (100, 5000.00, 0.00, NOW());

-- Insert open gig
INSERT INTO gig (gig_code, title, description, category, budget_min, budget_max, status, client_id, created_at, updated_at)
VALUES ('TEST-CANCEL-01', 'Logo Design for Startup', 'Need a modern logo design', 'Graphic Design', 300.00, 500.00, 'open', 100, NOW(), NOW());
-- Assume this creates gig ID = 1001

-- Now test cancellation via API:
-- POST /api/gigs/1001/cancel
-- Body: {"reason": "Client changed requirements"}

-- Or manually:
UPDATE gig SET status = 'cancelled', cancellation_reason = 'Client changed requirements', cancelled_at = NOW() WHERE id = 1001;


-- ============================================================================
-- SCENARIO 2: Cancel IN_PROGRESS gig WITH escrow (should trigger refund)
-- ============================================================================

-- Insert test freelancer
INSERT INTO "user" (username, email, password_hash, is_client, is_freelancer, is_verified, created_at)
VALUES ('cancel_test_freelancer1', 'cancelfreelancer1@test.com', 'pbkdf2:sha256:260000$test$test', FALSE, TRUE, TRUE, NOW());
-- Assume this creates user ID = 101

-- Insert freelancer wallet
INSERT INTO wallet (user_id, balance, held_balance, created_at)
VALUES (101, 0.00, 0.00, NOW());

-- Insert another client
INSERT INTO "user" (username, email, password_hash, is_client, is_freelancer, is_verified, created_at)
VALUES ('cancel_test_client2', 'cancelclient2@test.com', 'pbkdf2:sha256:260000$test$test', TRUE, FALSE, TRUE, NOW());
-- Assume this creates user ID = 102

-- Insert client wallet with funds
INSERT INTO wallet (user_id, balance, held_balance, created_at)
VALUES (102, 3000.00, 1500.00, NOW());

-- Insert in_progress gig with freelancer assigned
INSERT INTO gig (
    gig_code, title, description, category, budget_min, budget_max,
    approved_budget, agreed_amount, status, client_id, freelancer_id,
    created_at, updated_at
)
VALUES (
    'TEST-CANCEL-02',
    'Mobile App Development',
    'Build a mobile app for food delivery',
    'Mobile Development',
    1000.00,
    2000.00,
    1500.00,
    1500.00,
    'in_progress',
    102,  -- client_id
    101,  -- freelancer_id
    NOW(),
    NOW()
);
-- Assume this creates gig ID = 1002

-- Insert funded escrow
INSERT INTO escrow (
    escrow_number, gig_id, client_id, freelancer_id,
    amount, platform_fee, net_amount, status,
    payment_gateway, payment_reference,
    created_at, funded_at
)
VALUES (
    'ESC-CANCEL-TEST-02',
    1002,  -- gig_id
    102,   -- client_id
    101,   -- freelancer_id
    1500.00,
    75.00,   -- 5% fee
    1425.00,
    'funded',
    'stripe',
    'pi_test_cancel_123',
    NOW(),
    NOW()
);

-- Now test cancellation via API:
-- POST /api/gigs/1002/cancel
-- Body: {"reason": "Project scope changed significantly"}

-- This should:
-- 1. Set gig.status = 'cancelled'
-- 2. Set escrow.status = 'refunded'
-- 3. Update client wallet: held_balance -= 1500, balance += 1500 (if not Stripe)
-- 4. Create payment_history record
-- 5. Send notification to freelancer


-- ============================================================================
-- SCENARIO 3: Cancel PENDING_REVIEW gig (work submitted, awaiting approval)
-- ============================================================================

INSERT INTO gig (
    gig_code, title, description, category, budget_min, budget_max,
    approved_budget, agreed_amount, status, client_id, freelancer_id,
    created_at, updated_at
)
VALUES (
    'TEST-CANCEL-03',
    'Content Writing Project',
    'Write 10 blog posts about technology',
    'Writing',
    500.00,
    800.00,
    700.00,
    700.00,
    'pending_review',
    102,  -- client_id
    101,  -- freelancer_id
    NOW(),
    NOW()
);
-- Assume this creates gig ID = 1003

-- Insert funded escrow
INSERT INTO escrow (
    escrow_number, gig_id, client_id, freelancer_id,
    amount, platform_fee, net_amount, status,
    payment_gateway, created_at, funded_at
)
VALUES (
    'ESC-CANCEL-TEST-03',
    1003,
    102,
    101,
    700.00,
    35.00,
    665.00,
    'funded',
    'bank_transfer',
    NOW(),
    NOW()
);

-- Test cancellation:
-- POST /api/gigs/1003/cancel
-- Body: {"reason": "Quality not meeting expectations"}


-- ============================================================================
-- QUICK VERIFICATION QUERIES
-- ============================================================================

-- Check what gigs exist that can be cancelled
SELECT
    id,
    gig_code,
    title,
    status,
    client_id,
    freelancer_id,
    agreed_amount,
    cancellation_reason,
    cancelled_at
FROM gig
WHERE gig_code LIKE 'TEST-CANCEL-%'
ORDER BY id;

-- Check escrow status
SELECT
    e.escrow_number,
    g.gig_code,
    e.amount,
    e.status,
    e.refunded_amount,
    e.refunded_at
FROM escrow e
JOIN gig g ON e.gig_id = g.id
WHERE g.gig_code LIKE 'TEST-CANCEL-%';

-- Check wallet balances
SELECT
    u.username,
    w.balance,
    w.held_balance
FROM wallet w
JOIN "user" u ON w.user_id = u.id
WHERE u.username LIKE 'cancel_test_%';

-- Check notifications sent
SELECT
    n.notification_type,
    n.title,
    n.message,
    u.username as recipient,
    n.created_at
FROM notification n
JOIN "user" u ON n.user_id = u.id
WHERE n.title LIKE '%Cancel%'
ORDER BY n.created_at DESC
LIMIT 10;


-- ============================================================================
-- CLEANUP ALL TEST DATA
-- ============================================================================

DELETE FROM notification WHERE user_id IN (
    SELECT id FROM "user" WHERE username LIKE 'cancel_test_%'
);

DELETE FROM payment_history WHERE user_id IN (
    SELECT id FROM "user" WHERE username LIKE 'cancel_test_%'
);

DELETE FROM escrow WHERE escrow_number LIKE 'ESC-CANCEL-TEST-%';

DELETE FROM application WHERE gig_id IN (
    SELECT id FROM gig WHERE gig_code LIKE 'TEST-CANCEL-%'
);

DELETE FROM gig WHERE gig_code LIKE 'TEST-CANCEL-%';

DELETE FROM wallet WHERE user_id IN (
    SELECT id FROM "user" WHERE username LIKE 'cancel_test_%'
);

DELETE FROM "user" WHERE username LIKE 'cancel_test_%';
