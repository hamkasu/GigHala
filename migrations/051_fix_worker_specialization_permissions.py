#!/usr/bin/env python3
"""
Migration 051: Fix Worker Specialization Table Permissions

This migration grants the necessary PostgreSQL privileges on the
worker_specialization and worker_rate_audit tables to the application
database user extracted from DATABASE_URL.

Root cause: If migration 050 (or the original table creation) was run by a
different PostgreSQL role than the application user, the app user will receive
"permission denied for table worker_specialization" on every query.

Usage (two modes):

  Mode A – app user is a superuser / table owner (most common):
    python migrations/051_fix_worker_specialization_permissions.py

  Mode B – app user is NOT a superuser; supply a superuser URL via
  SUPERUSER_DATABASE_URL so the grants can be issued with elevated privileges:
    SUPERUSER_DATABASE_URL="postgresql://postgres:secret@host/db" \
    python migrations/051_fix_worker_specialization_permissions.py

This will:
1. Parse DATABASE_URL to determine the application database user
2. Connect via SUPERUSER_DATABASE_URL (or DATABASE_URL if not set)
3. GRANT ALL on worker_specialization
4. GRANT ALL on worker_rate_audit
5. GRANT USAGE, SELECT on associated sequences (for SERIAL primary keys)
6. Verify the grants were applied successfully
"""

import os
import sys
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text


def get_db_username(database_url):
    """Extract the username from a DATABASE_URL connection string."""
    parsed = urlparse(database_url)
    return parsed.username


def run_migration():
    database_url = os.environ.get('DATABASE_URL', '')
    # Optional: a superuser URL used only to issue the GRANTs.
    # When the app DATABASE_URL user is not a superuser/table-owner,
    # set SUPERUSER_DATABASE_URL to a postgres superuser connection string.
    superuser_url = os.environ.get('SUPERUSER_DATABASE_URL', '') or database_url

    if not database_url:
        print("ERROR: DATABASE_URL environment variable is not set.")
        return False

    is_postgres = 'postgresql' in database_url or 'postgres' in database_url

    print("=" * 60)
    print("Migration 051: Fix Worker Specialization Permissions")
    print("=" * 60)

    if not is_postgres:
        print("Database type: SQLite")
        print("SQLite does not use role-based permissions - no action needed.")
        return True

    app_user = get_db_username(database_url)
    if not app_user:
        print("ERROR: Could not extract username from DATABASE_URL.")
        return False

    print(f"Database type: PostgreSQL")
    print(f"Application DB user (grantee): {app_user}")

    # Normalise the URL so psycopg2 accepts it (postgres:// -> postgresql://)
    def _normalise(url):
        if url.startswith('postgres://'):
            return url.replace('postgres://', 'postgresql://', 1)
        return url

    grant_url = _normalise(superuser_url)
    grant_user = get_db_username(grant_url)
    if grant_user and grant_user != app_user:
        print(f"Granting via superuser URL (user: {grant_user})")
    print()

    engine = create_engine(grant_url)

    statements = [
        # worker_specialization – full DML privileges
        f'GRANT ALL ON TABLE worker_specialization TO "{app_user}"',
        # worker_rate_audit – full DML privileges
        f'GRANT ALL ON TABLE worker_rate_audit TO "{app_user}"',
        # Sequences used by SERIAL / BIGSERIAL primary keys
        f'GRANT USAGE, SELECT ON SEQUENCE worker_specialization_id_seq TO "{app_user}"',
        f'GRANT USAGE, SELECT ON SEQUENCE worker_rate_audit_id_seq TO "{app_user}"',
    ]

    success_count = 0
    skip_count = 0
    error_count = 0

    with engine.connect() as conn:
        for stmt in statements:
            try:
                conn.execute(text(stmt))
                conn.commit()
                success_count += 1
                print(f"[OK]   {stmt}")
            except Exception as e:
                err = str(e).lower()
                # "already has privilege" is harmless
                if 'already' in err and 'privilege' in err:
                    skip_count += 1
                    print(f"[SKIP] {stmt} (privilege already granted)")
                    conn.rollback()
                elif 'does not exist' in err:
                    # Sequence names can vary; try common alternatives
                    skip_count += 1
                    print(f"[SKIP] {stmt} (object does not exist, may use different sequence name)")
                    conn.rollback()
                else:
                    error_count += 1
                    print(f"[ERROR] {stmt}")
                    print(f"        {e}")
                    conn.rollback()

    print()
    print("=" * 60)
    print("Migration Summary")
    print("=" * 60)
    print(f"Successful : {success_count}")
    print(f"Skipped    : {skip_count}")
    print(f"Errors     : {error_count}")
    print()

    if error_count > 0:
        print("Migration completed with errors.")
        print()
        print("The GRANT failed because the connecting user is not the table owner")
        print("and not a superuser.  Retry with a superuser connection:")
        print()
        print("  SUPERUSER_DATABASE_URL='postgresql://postgres:secret@host/db' \\")
        print("  python migrations/051_fix_worker_specialization_permissions.py")
        print()
        print("Or connect as a superuser in psql and run:")
        print()
        print(f'  GRANT ALL ON TABLE worker_specialization TO "{app_user}";')
        print(f'  GRANT ALL ON TABLE worker_rate_audit TO "{app_user}";')
        print(f'  GRANT ALL ON SEQUENCE worker_specialization_id_seq TO "{app_user}";')
        print(f'  GRANT ALL ON SEQUENCE worker_rate_audit_id_seq TO "{app_user}";')
        print()
        return False

    print("Permissions granted successfully!")
    return True


def verify_migration():
    """Verify the application user can now query worker_specialization."""
    database_url = os.environ.get('DATABASE_URL', '')
    if not database_url:
        return

    is_postgres = 'postgresql' in database_url or 'postgres' in database_url
    if not is_postgres:
        return

    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)

    print()
    print("=" * 60)
    print("Verifying Permissions")
    print("=" * 60)

    engine = create_engine(database_url)

    checks = [
        ("SELECT on worker_specialization",
         "SELECT COUNT(*) FROM worker_specialization"),
        ("SELECT on worker_rate_audit",
         "SELECT COUNT(*) FROM worker_rate_audit"),
    ]

    for label, query in checks:
        try:
            with engine.connect() as conn:
                conn.execute(text(query))
            print(f"[OK] {label}")
        except Exception as e:
            print(f"[FAIL] {label}: {e}")

    print()
    print("Verification complete.")


if __name__ == '__main__':
    success = run_migration()
    if success:
        verify_migration()
    sys.exit(0 if success else 1)
