-- ============================================
-- GigHala Database Role Separation Migration
-- Implements Principle of Least Privilege
-- ============================================
--
-- This script creates separate database roles:
-- 1. gighala_admin - Full privileges for migrations and maintenance
-- 2. gighala_app   - Limited privileges for production runtime
--
-- IMPORTANT: Run this script as the PostgreSQL superuser (postgres)
-- ============================================

-- ============================================
-- STEP 1: Create Database Roles
-- ============================================

-- Admin role for migrations, schema changes, and maintenance
CREATE ROLE gighala_admin WITH LOGIN PASSWORD 'CHANGE_THIS_ADMIN_PASSWORD';

-- App role for production runtime (limited privileges)
CREATE ROLE gighala_app WITH LOGIN PASSWORD 'CHANGE_THIS_APP_PASSWORD';

-- ============================================
-- STEP 2: Grant Database-Level Privileges
-- ============================================

-- Admin gets full privileges
GRANT ALL PRIVILEGES ON DATABASE gighala TO gighala_admin;

-- App gets connection privileges only (table privileges below)
GRANT CONNECT ON DATABASE gighala TO gighala_app;

-- ============================================
-- STEP 3: Grant Schema Privileges
-- ============================================

-- Admin gets full schema privileges
GRANT ALL ON SCHEMA public TO gighala_admin;

-- App gets usage on public schema
GRANT USAGE ON SCHEMA public TO gighala_app;

-- ============================================
-- STEP 4: Grant Table Privileges (Existing Tables)
-- ============================================

-- Admin gets all privileges on all existing tables
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO gighala_admin;

-- App gets limited privileges on all existing tables
-- SELECT - Read data
-- INSERT - Create new records
-- UPDATE - Modify existing records
-- DELETE - Remove records (needed for user-initiated deletions)
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO gighala_app;

-- ============================================
-- STEP 5: Grant Sequence Privileges (for SERIAL/AUTO_INCREMENT)
-- ============================================

-- Admin gets all privileges on sequences
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO gighala_admin;

-- App needs USAGE and SELECT on sequences to insert records with auto-increment IDs
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO gighala_app;

-- ============================================
-- STEP 6: Set Default Privileges for Future Objects
-- ============================================

-- When gighala_admin creates new tables, grant privileges automatically

-- Default privileges for tables created by admin
ALTER DEFAULT PRIVILEGES FOR ROLE gighala_admin IN SCHEMA public
GRANT ALL PRIVILEGES ON TABLES TO gighala_admin;

ALTER DEFAULT PRIVILEGES FOR ROLE gighala_admin IN SCHEMA public
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO gighala_app;

-- Default privileges for sequences created by admin
ALTER DEFAULT PRIVILEGES FOR ROLE gighala_admin IN SCHEMA public
GRANT ALL PRIVILEGES ON SEQUENCES TO gighala_admin;

ALTER DEFAULT PRIVILEGES FOR ROLE gighala_admin IN SCHEMA public
GRANT USAGE, SELECT ON SEQUENCES TO gighala_app;

-- Default privileges for functions created by admin
ALTER DEFAULT PRIVILEGES FOR ROLE gighala_admin IN SCHEMA public
GRANT ALL PRIVILEGES ON FUNCTIONS TO gighala_admin;

ALTER DEFAULT PRIVILEGES FOR ROLE gighala_admin IN SCHEMA public
GRANT EXECUTE ON FUNCTIONS TO gighala_app;

-- ============================================
-- STEP 7: Ownership Transfer (OPTIONAL)
-- ============================================
-- If you want to transfer ownership of existing tables to gighala_admin
-- Uncomment the following section after replacing YOUR_CURRENT_OWNER

/*
-- Transfer table ownership
DO $$
DECLARE
    tbl record;
BEGIN
    FOR tbl IN
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'public'
    LOOP
        EXECUTE 'ALTER TABLE public.' || quote_ident(tbl.tablename) || ' OWNER TO gighala_admin';
    END LOOP;
END $$;

-- Transfer sequence ownership
DO $$
DECLARE
    seq record;
BEGIN
    FOR seq IN
        SELECT sequencename
        FROM pg_sequences
        WHERE schemaname = 'public'
    LOOP
        EXECUTE 'ALTER SEQUENCE public.' || quote_ident(seq.sequencename) || ' OWNER TO gighala_admin';
    END LOOP;
END $$;
*/

-- ============================================
-- STEP 8: Verify Privileges (Run as postgres)
-- ============================================

-- Verify roles were created
-- SELECT rolname, rolsuper, rolcreaterole, rolcreatedb FROM pg_roles WHERE rolname LIKE 'gighala%';

-- Verify table privileges for gighala_app
-- SELECT grantee, privilege_type, table_name
-- FROM information_schema.role_table_grants
-- WHERE grantee = 'gighala_app'
-- ORDER BY table_name, privilege_type;

-- Verify sequence privileges for gighala_app
-- SELECT grantee, privilege_type, object_name
-- FROM information_schema.usage_privileges
-- WHERE grantee = 'gighala_app' AND object_type = 'SEQUENCE';

-- ============================================
-- SECURITY NOTES
-- ============================================
--
-- 1. The gighala_app role CANNOT:
--    - DROP tables or databases
--    - CREATE new tables
--    - ALTER table schemas
--    - Create or modify roles
--    - Access other databases
--
-- 2. The gighala_admin role SHOULD:
--    - Only be used for migrations
--    - Never be used in production application code
--    - Have different credentials from gighala_app
--    - Be stored securely (separate from app credentials)
--
-- 3. In your application:
--    - Use DATABASE_URL with gighala_app credentials
--    - Use DATABASE_ADMIN_URL with gighala_admin credentials (migrations only)
--
-- 4. Connection string format:
--    DATABASE_URL=postgresql://gighala_app:PASSWORD@host:5432/gighala
--    DATABASE_ADMIN_URL=postgresql://gighala_admin:PASSWORD@host:5432/gighala
--
-- ============================================
-- ROLLBACK (if needed)
-- ============================================
/*
-- To remove the roles (WARNING: This will revoke all privileges)
REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM gighala_app;
REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM gighala_app;
REVOKE ALL PRIVILEGES ON SCHEMA public FROM gighala_app;
REVOKE CONNECT ON DATABASE gighala FROM gighala_app;

REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM gighala_admin;
REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM gighala_admin;
REVOKE ALL PRIVILEGES ON SCHEMA public FROM gighala_admin;
REVOKE ALL PRIVILEGES ON DATABASE gighala FROM gighala_admin;

DROP ROLE gighala_app;
DROP ROLE gighala_admin;
*/
