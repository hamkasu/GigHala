-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================
-- Run these queries after migration to verify everything is set up correctly
-- Works for both PostgreSQL and SQLite

-- ============================================================================
-- FOR POSTGRESQL
-- ============================================================================

-- Check if Invoice table exists and view its structure
SELECT table_name
FROM information_schema.tables
WHERE table_name = 'invoice';

-- View all Invoice table columns
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'invoice'
ORDER BY ordinal_position;

-- Check if Receipt table exists and view its structure
SELECT table_name
FROM information_schema.tables
WHERE table_name = 'receipt';

-- View all Receipt table columns
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'receipt'
ORDER BY ordinal_position;

-- Check if Notification table exists and view its structure
SELECT table_name
FROM information_schema.tables
WHERE table_name = 'notification';

-- View all Notification table columns
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'notification'
ORDER BY ordinal_position;

-- Check all indexes on Invoice table
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'invoice';

-- Check all indexes on Receipt table
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'receipt';

-- Check all indexes on Notification table
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'notification';

-- Count existing records (should be 0 for new tables)
SELECT 'invoice' as table_name, COUNT(*) as record_count FROM invoice
UNION ALL
SELECT 'receipt' as table_name, COUNT(*) as record_count FROM receipt
UNION ALL
SELECT 'notification' as table_name, COUNT(*) as record_count FROM notification;


-- ============================================================================
-- FOR SQLITE
-- ============================================================================

-- Check if Invoice table exists and view its structure
.tables invoice

-- View Invoice table schema
.schema invoice

-- View Invoice table columns
PRAGMA table_info(invoice);

-- Check if Receipt table exists and view its structure
.tables receipt

-- View Receipt table schema
.schema receipt

-- View Receipt table columns
PRAGMA table_info(receipt);

-- Check if Notification table exists and view its structure
.tables notification

-- View Notification table schema
.schema notification

-- View Notification table columns
PRAGMA table_info(notification);

-- Check indexes on Invoice table
PRAGMA index_list(invoice);

-- Check indexes on Receipt table
PRAGMA index_list(receipt);

-- Check indexes on Notification table
PRAGMA index_list(notification);

-- Count existing records (should be 0 for new tables)
SELECT 'invoice' as table_name, COUNT(*) as record_count FROM invoice
UNION ALL
SELECT 'receipt' as table_name, COUNT(*) as record_count FROM receipt
UNION ALL
SELECT 'notification' as table_name, COUNT(*) as record_count FROM notification;


-- ============================================================================
-- UNIVERSAL QUERIES (work on both PostgreSQL and SQLite)
-- ============================================================================

-- Test that foreign keys are set up correctly
SELECT
    i.id as invoice_id,
    i.invoice_number,
    i.gig_id,
    g.title as gig_title
FROM invoice i
LEFT JOIN gig g ON i.gig_id = g.id
LIMIT 5;

-- Test that receipt links to invoice
SELECT
    r.id as receipt_id,
    r.receipt_number,
    r.invoice_id,
    i.invoice_number
FROM receipt r
LEFT JOIN invoice i ON r.invoice_id = i.id
LIMIT 5;

-- Test that notifications link correctly
SELECT
    n.id as notification_id,
    n.title,
    n.notification_type,
    n.related_id,
    n.link
FROM notification n
WHERE n.notification_type IN ('payment', 'work_completed')
LIMIT 5;

-- Check invoice statuses (should have valid values)
SELECT DISTINCT status FROM invoice;

-- Check receipt types (should have valid values)
SELECT DISTINCT receipt_type FROM receipt;

-- Check notification types
SELECT DISTINCT notification_type FROM notification;


-- ============================================================================
-- EXPECTED RESULTS
-- ============================================================================
-- After a fresh migration, you should see:
--
-- ✅ Tables: invoice, receipt, notification all exist
-- ✅ Invoice columns: invoice_number, due_date, paid_at, payment_reference, notes
-- ✅ Receipt columns: receipt_number, receipt_type, invoice_id, description
-- ✅ Notification columns: related_id, link
-- ✅ Multiple indexes on each table (at least 5-6 per table)
-- ✅ Record count: 0 for new tables (or existing data if upgrading)
--
-- If any of these are missing, re-run the appropriate ALTER TABLE commands
-- from MANUAL_POSTGRESQL.sql or MANUAL_SQLITE.sql
