-- Manual SQL Insert Queries for Testing Gig Cancellation System
-- Execute these queries in order to create test data

-- ============================================================================
-- 1. CREATE TEST CLIENT USER
-- ============================================================================
INSERT INTO "user" (
    username,
    email,
    password_hash,
    is_client,
    is_freelancer,
    is_verified,
    created_at
) VALUES (
    'test_client',
    'client@test.com',
    'scrypt:32768:8:1$fake_hash_replace_with_real',  -- Replace with actual hash
    TRUE,
    FALSE,
    TRUE,
    NOW()
) RETURNING id;  -- Note the returned ID for use below

-- For SQLite, use: datetime('now') instead of NOW()

-- ============================================================================
-- 2. CREATE TEST FREELANCER USER
-- ============================================================================
INSERT INTO "user" (
    username,
    email,
    password_hash,
    is_client,
    is_freelancer,
    is_verified,
    created_at
) VALUES (
    'test_freelancer',
    'freelancer@test.com',
    'scrypt:32768:8:1$fake_hash_replace_with_real',  -- Replace with actual hash
    FALSE,
    TRUE,
    TRUE,
    NOW()
) RETURNING id;  -- Note the returned ID for use below

-- ============================================================================
-- 3. CREATE TEST WALLETS FOR BOTH USERS
-- ============================================================================
-- Client wallet
INSERT INTO wallet (
    user_id,
    balance,
    held_balance,
    created_at
) VALUES (
    1,  -- Replace with actual client user_id from step 1
    1000.00,
    0.00,
    NOW()
);

-- Freelancer wallet
INSERT INTO wallet (
    user_id,
    balance,
    held_balance,
    created_at
) VALUES (
    2,  -- Replace with actual freelancer user_id from step 2
    0.00,
    0.00,
    NOW()
);

-- ============================================================================
-- 4. CREATE TEST GIG (OPEN STATUS - NO FREELANCER ASSIGNED)
-- ============================================================================
INSERT INTO gig (
    gig_code,
    title,
    description,
    category,
    budget_min,
    budget_max,
    duration,
    location,
    is_remote,
    status,
    client_id,
    halal_compliant,
    halal_verified,
    created_at,
    updated_at
) VALUES (
    'GIG-TEST-001',
    'Test Gig - Open Status',
    'This is a test gig in open status for testing cancellation',
    'Web Development',
    500.00,
    1000.00,
    '1 week',
    'Kuala Lumpur',
    TRUE,
    'open',
    1,  -- Replace with actual client user_id
    TRUE,
    FALSE,
    NOW(),
    NOW()
) RETURNING id;

-- ============================================================================
-- 5. CREATE TEST GIG (IN_PROGRESS STATUS - WITH FREELANCER)
-- ============================================================================
INSERT INTO gig (
    gig_code,
    title,
    description,
    category,
    budget_min,
    budget_max,
    approved_budget,
    agreed_amount,
    duration,
    location,
    is_remote,
    status,
    client_id,
    freelancer_id,
    halal_compliant,
    halal_verified,
    created_at,
    updated_at
) VALUES (
    'GIG-TEST-002',
    'Test Gig - In Progress',
    'This is a test gig in progress for testing cancellation with refund',
    'Graphic Design',
    800.00,
    1500.00,
    1200.00,
    1200.00,
    '2 weeks',
    'Kuala Lumpur',
    TRUE,
    'in_progress',
    1,  -- Replace with actual client user_id
    2,  -- Replace with actual freelancer user_id
    TRUE,
    FALSE,
    NOW(),
    NOW()
) RETURNING id;

-- ============================================================================
-- 6. CREATE APPLICATION FOR THE OPEN GIG
-- ============================================================================
INSERT INTO application (
    gig_id,
    freelancer_id,
    cover_letter,
    proposed_price,
    status,
    created_at
) VALUES (
    1,  -- Replace with gig_id from step 4
    2,  -- Replace with freelancer user_id
    'I am very interested in this project and have the necessary skills.',
    750.00,
    'pending',
    NOW()
);

-- ============================================================================
-- 7. CREATE ESCROW FOR THE IN_PROGRESS GIG
-- ============================================================================
INSERT INTO escrow (
    escrow_number,
    gig_id,
    client_id,
    freelancer_id,
    amount,
    platform_fee,
    net_amount,
    status,
    payment_gateway,
    payment_reference,
    created_at,
    funded_at
) VALUES (
    'ESC-TEST-001',
    2,  -- Replace with gig_id from step 5 (in_progress gig)
    1,  -- Replace with client user_id
    2,  -- Replace with freelancer user_id
    1200.00,
    60.00,  -- 5% platform fee
    1140.00,
    'funded',
    'stripe',
    'pi_test_123456789',
    NOW(),
    NOW()
);

-- ============================================================================
-- 8. UPDATE CLIENT WALLET TO REFLECT HELD BALANCE
-- ============================================================================
UPDATE wallet
SET held_balance = 1200.00,
    balance = balance - 1200.00
WHERE user_id = 1;  -- Replace with client user_id

-- ============================================================================
-- 9. CREATE PAYMENT HISTORY FOR ESCROW FUNDING
-- ============================================================================
INSERT INTO payment_history (
    user_id,
    type,
    amount,
    balance_before,
    balance_after,
    description,
    reference_number,
    payment_gateway,
    status,
    created_at
) VALUES (
    1,  -- Client user_id
    'escrow_funding',
    1200.00,
    1000.00,
    0.00,
    'Escrow funding for gig: Test Gig - In Progress',
    'pi_test_123456789',
    'stripe',
    'completed',
    NOW()
);

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Check created users
SELECT id, username, email, is_client, is_freelancer FROM "user"
WHERE username IN ('test_client', 'test_freelancer');

-- Check created gigs
SELECT id, gig_code, title, status, client_id, freelancer_id, agreed_amount
FROM gig
WHERE gig_code LIKE 'GIG-TEST-%';

-- Check escrow
SELECT escrow_number, gig_id, amount, status, payment_gateway
FROM escrow
WHERE escrow_number = 'ESC-TEST-001';

-- Check wallet balances
SELECT u.username, w.balance, w.held_balance
FROM wallet w
JOIN "user" u ON w.user_id = u.id
WHERE u.username IN ('test_client', 'test_freelancer');

-- ============================================================================
-- MANUAL CANCELLATION TEST QUERIES
-- ============================================================================

-- To manually test cancellation (simulating the API call):
UPDATE gig
SET
    status = 'cancelled',
    cancellation_reason = 'Manual test cancellation - testing the system',
    cancelled_at = NOW()
WHERE gig_code = 'GIG-TEST-001';

-- To manually process refund for in_progress gig:
UPDATE gig
SET
    status = 'cancelled',
    cancellation_reason = 'Testing cancellation with escrow refund',
    cancelled_at = NOW()
WHERE gig_code = 'GIG-TEST-002';

UPDATE escrow
SET
    status = 'refunded',
    refunded_amount = amount,
    refunded_at = NOW()
WHERE gig_id = (SELECT id FROM gig WHERE gig_code = 'GIG-TEST-002');

UPDATE wallet
SET
    held_balance = held_balance - 1200.00,
    balance = balance + 1200.00
WHERE user_id = 1;  -- Client gets refund

-- ============================================================================
-- CLEANUP QUERIES (Run these to remove test data)
-- ============================================================================

-- Delete in reverse order due to foreign key constraints
DELETE FROM payment_history WHERE user_id IN (
    SELECT id FROM "user" WHERE username IN ('test_client', 'test_freelancer')
);

DELETE FROM escrow WHERE gig_id IN (
    SELECT id FROM gig WHERE gig_code LIKE 'GIG-TEST-%'
);

DELETE FROM application WHERE gig_id IN (
    SELECT id FROM gig WHERE gig_code LIKE 'GIG-TEST-%'
);

DELETE FROM gig WHERE gig_code LIKE 'GIG-TEST-%';

DELETE FROM wallet WHERE user_id IN (
    SELECT id FROM "user" WHERE username IN ('test_client', 'test_freelancer')
);

DELETE FROM "user" WHERE username IN ('test_client', 'test_freelancer');

-- Verify cleanup
SELECT COUNT(*) as remaining_test_gigs FROM gig WHERE gig_code LIKE 'GIG-TEST-%';
SELECT COUNT(*) as remaining_test_users FROM "user" WHERE username IN ('test_client', 'test_freelancer');
