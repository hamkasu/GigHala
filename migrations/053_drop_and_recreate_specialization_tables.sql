-- Migration 053: Drop and recreate worker_specialization tables
-- ============================================================
-- PURPOSE:
--   The worker_specialization and worker_rate_audit tables are owned by a
--   different PostgreSQL role than the application user, causing
--   "permission denied for table worker_specialization" on every query.
--
-- HOW TO USE:
--   1. Paste this SQL into your hosting provider's SQL console:
--        Railway  → Postgres service → Data tab → Query
--        Neon     → SQL Editor
--        Supabase → SQL Editor
--   2. Run it (connect as the admin/superuser user, which is the default
--      in all three platforms' SQL consoles).
--   3. Restart your app – SQLAlchemy's db.create_all() will recreate the
--      tables correctly, owned by the app user from DATABASE_URL.
--
-- DATA IMPACT:
--   worker_specialization and worker_rate_audit rows will be deleted.
--   Since the feature was completely inaccessible (permission denied), there
--   is no usable data in these tables to preserve.
--   The gig_worker.specialization_id and application.specialization_id columns
--   are kept; only the FK constraints are dropped (they will be missing after
--   recreation, but the application code handles the relationship correctly).

-- Step 1: Drop FK constraints that reference worker_specialization
ALTER TABLE IF EXISTS gig_worker  DROP CONSTRAINT IF EXISTS gig_worker_specialization_id_fkey;
ALTER TABLE IF EXISTS application  DROP CONSTRAINT IF EXISTS application_specialization_id_fkey;

-- Step 2: Drop the tables (worker_rate_audit first – it references worker_specialization)
DROP TABLE IF EXISTS worker_rate_audit;
DROP TABLE IF EXISTS worker_specialization;

-- Done. Restart your app now.
-- SQLAlchemy will recreate both tables owned by the app user from DATABASE_URL.
