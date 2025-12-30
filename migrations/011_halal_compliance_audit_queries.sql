-- ============================================================================
-- HALAL COMPLIANCE SYSTEM - OPTIONAL AUDIT QUERIES
-- ============================================================================
-- These queries help you audit existing data and optimize the database
-- for the new Halal Compliance System.
--
-- Run these queries manually as needed - they are NOT required for the
-- system to work, but they help with data validation and optimization.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. AUDIT EXISTING GIGS
-- ----------------------------------------------------------------------------

-- Count gigs by halal compliance status
SELECT
    halal_compliant,
    halal_verified,
    COUNT(*) as gig_count
FROM gig
GROUP BY halal_compliant, halal_verified;

-- Find gigs that are NOT marked as halal compliant (may need review)
SELECT
    id,
    gig_code,
    title,
    category,
    status,
    client_id,
    created_at
FROM gig
WHERE halal_compliant = false
ORDER BY created_at DESC;

-- Find open gigs that need halal verification
SELECT
    id,
    gig_code,
    title,
    category,
    halal_compliant,
    halal_verified,
    created_at
FROM gig
WHERE status = 'open'
  AND halal_compliant = true
  AND halal_verified = false
ORDER BY created_at DESC
LIMIT 100;

-- ----------------------------------------------------------------------------
-- 2. CHECK FOR POTENTIAL VIOLATIONS IN EXISTING DATA
-- ----------------------------------------------------------------------------

-- IMPORTANT: Run these queries to find gigs that might have slipped through
-- before the halal compliance system was implemented.

-- Check for alcohol-related keywords in titles
SELECT
    id,
    gig_code,
    title,
    category,
    status,
    halal_compliant
FROM gig
WHERE LOWER(title) ~ '\y(alcohol|beer|wine|whiskey|vodka|rum|arak|bir|alkohol)\y'
   OR LOWER(description) ~ '\y(alcohol|beer|wine|whiskey|vodka|rum|arak|bir|alkohol)\y'
ORDER BY created_at DESC;

-- Check for gambling-related keywords
SELECT
    id,
    gig_code,
    title,
    category,
    status,
    halal_compliant
FROM gig
WHERE LOWER(title) ~ '\y(gambling|casino|betting|lottery|judi|kasino|pertaruhan|loteri)\y'
   OR LOWER(description) ~ '\y(gambling|casino|betting|lottery|judi|kasino|pertaruhan|loteri)\y'
ORDER BY created_at DESC;

-- Check for adult content keywords
SELECT
    id,
    gig_code,
    title,
    category,
    status,
    halal_compliant
FROM gig
WHERE LOWER(title) ~ '\y(porn|adult|xxx|escort|sex|seks|pornografi)\y'
   OR LOWER(description) ~ '\y(porn|adult|xxx|escort|sex|seks|pornografi)\y'
ORDER BY created_at DESC;

-- Check for riba/interest keywords
SELECT
    id,
    gig_code,
    title,
    category,
    status,
    halal_compliant
FROM gig
WHERE LOWER(title) ~ '\y(interest|riba|usury|faedah|loan shark|along)\y'
   OR LOWER(description) ~ '\y(interest|riba|usury|faedah|loan shark|along)\y'
ORDER BY created_at DESC;

-- ----------------------------------------------------------------------------
-- 3. CATEGORY VALIDATION
-- ----------------------------------------------------------------------------

-- Check if any gigs have categories not in the approved list
-- (This should not happen after the system is deployed)
WITH approved_categories AS (
    SELECT UNNEST(ARRAY[
        'design', 'writing', 'video', 'tutoring', 'content', 'web',
        'marketing', 'admin', 'general', 'programming', 'consulting',
        'engineering', 'music', 'photography', 'finance', 'crafts',
        'garden', 'coaching', 'data', 'pets', 'handyman', 'tours',
        'events', 'online-selling', 'virtual-assistant', 'delivery',
        'micro-tasks', 'caregiving', 'creative-other'
    ]) AS slug
)
SELECT
    g.id,
    g.gig_code,
    g.title,
    g.category,
    g.status
FROM gig g
WHERE g.category NOT IN (SELECT slug FROM approved_categories)
ORDER BY g.created_at DESC;

-- ----------------------------------------------------------------------------
-- 4. PERFORMANCE OPTIMIZATION - ADD INDEXES
-- ----------------------------------------------------------------------------

-- Add indexes for faster halal compliance filtering
-- (Run these if they don't already exist)

CREATE INDEX IF NOT EXISTS idx_gig_halal_compliant
ON gig(halal_compliant) WHERE status = 'open';

CREATE INDEX IF NOT EXISTS idx_gig_halal_verified
ON gig(halal_verified) WHERE status = 'open';

CREATE INDEX IF NOT EXISTS idx_gig_halal_status
ON gig(halal_compliant, halal_verified, status);

CREATE INDEX IF NOT EXISTS idx_gig_category_halal
ON gig(category, halal_compliant) WHERE status = 'open';

-- Full-text search index for keyword detection (PostgreSQL)
-- This speeds up violation detection queries
CREATE INDEX IF NOT EXISTS idx_gig_title_trgm
ON gig USING gin (LOWER(title) gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_gig_description_trgm
ON gig USING gin (LOWER(description) gin_trgm_ops);

-- Note: The above requires the pg_trgm extension
-- Run this first if you get an error:
-- CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ----------------------------------------------------------------------------
-- 5. SECURITY EVENT LOGGING - CHECK TABLE EXISTS
-- ----------------------------------------------------------------------------

-- Verify the security_event table exists (should be created by migration 006)
SELECT EXISTS (
    SELECT FROM information_schema.tables
    WHERE table_name = 'security_event'
) AS security_event_table_exists;

-- If the table exists, check for halal violation logs
SELECT
    event_type,
    user_id,
    details,
    created_at
FROM security_event
WHERE event_type = 'halal_violation_attempt'
ORDER BY created_at DESC
LIMIT 20;

-- Count halal violations by user (to identify repeat offenders)
SELECT
    user_id,
    u.username,
    u.email,
    COUNT(*) as violation_count,
    MAX(se.created_at) as last_violation
FROM security_event se
LEFT JOIN "user" u ON u.id = se.user_id
WHERE se.event_type = 'halal_violation_attempt'
GROUP BY user_id, u.username, u.email
ORDER BY violation_count DESC;

-- ----------------------------------------------------------------------------
-- 6. OPTIONAL: BULK UPDATE EXISTING GIGS
-- ----------------------------------------------------------------------------

-- If you want to mark all existing gigs as halal_compliant = true by default
-- (Only run this if you're confident existing gigs are halal)
--
-- CAUTION: Review existing gigs first using the audit queries above!

-- UPDATE gig
-- SET halal_compliant = true
-- WHERE halal_compliant IS NULL OR halal_compliant = false;

-- If you want to require admin review for all existing gigs:
-- UPDATE gig
-- SET halal_verified = false
-- WHERE created_at < '2025-01-15 00:00:00';  -- Adjust date as needed

-- ----------------------------------------------------------------------------
-- 7. MONITORING QUERIES (for ongoing compliance tracking)
-- ----------------------------------------------------------------------------

-- Daily halal violations summary
SELECT
    DATE(created_at) as violation_date,
    COUNT(*) as violation_count,
    COUNT(DISTINCT user_id) as unique_users
FROM security_event
WHERE event_type = 'halal_violation_attempt'
  AND created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY violation_date DESC;

-- Most common violation keywords
SELECT
    jsonb_array_elements_text(details->'violations'->'title') as keyword,
    COUNT(*) as frequency
FROM security_event
WHERE event_type = 'halal_violation_attempt'
  AND details->'violations'->'title' IS NOT NULL
GROUP BY keyword
ORDER BY frequency DESC
LIMIT 20;

-- Gigs created per day with halal status
SELECT
    DATE(created_at) as creation_date,
    COUNT(*) as total_gigs,
    SUM(CASE WHEN halal_compliant THEN 1 ELSE 0 END) as halal_gigs,
    SUM(CASE WHEN NOT halal_compliant THEN 1 ELSE 0 END) as non_halal_gigs,
    SUM(CASE WHEN halal_verified THEN 1 ELSE 0 END) as verified_gigs
FROM gig
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY creation_date DESC;

-- ----------------------------------------------------------------------------
-- 8. USER COMPLIANCE SCORE (for future enhancement)
-- ----------------------------------------------------------------------------

-- Calculate compliance score per user (for future implementation)
SELECT
    u.id,
    u.username,
    u.email,
    COUNT(g.id) as total_gigs_posted,
    SUM(CASE WHEN g.halal_compliant THEN 1 ELSE 0 END) as halal_gigs,
    COUNT(se.id) as violation_attempts,
    ROUND(
        100.0 * SUM(CASE WHEN g.halal_compliant THEN 1 ELSE 0 END) / NULLIF(COUNT(g.id), 0),
        2
    ) as compliance_percentage
FROM "user" u
LEFT JOIN gig g ON g.client_id = u.id
LEFT JOIN security_event se ON se.user_id = u.id AND se.event_type = 'halal_violation_attempt'
WHERE u.user_type IN ('client', 'both')
GROUP BY u.id, u.username, u.email
HAVING COUNT(g.id) > 0
ORDER BY violation_attempts DESC, compliance_percentage ASC;

-- ============================================================================
-- SQLITE VERSIONS (if using SQLite instead of PostgreSQL)
-- ============================================================================

-- For SQLite, use LIKE instead of ~ for pattern matching:

-- Example: Check for alcohol keywords in SQLite
-- SELECT
--     id, gig_code, title, category, status, halal_compliant
-- FROM gig
-- WHERE LOWER(title) LIKE '%alcohol%'
--    OR LOWER(title) LIKE '%beer%'
--    OR LOWER(title) LIKE '%wine%'
--    OR LOWER(description) LIKE '%alcohol%'
--    OR LOWER(description) LIKE '%beer%'
-- ORDER BY created_at DESC;

-- ============================================================================
-- END OF AUDIT QUERIES
-- ============================================================================

-- RECOMMENDATIONS:
-- 1. Run the audit queries (sections 1-2) to check existing data
-- 2. Run the index creation queries (section 4) for better performance
-- 3. Set up a cron job to run monitoring queries (section 7) daily
-- 4. Review violation logs weekly to identify patterns
-- 5. Consider implementing user compliance scoring (section 8) in the future
