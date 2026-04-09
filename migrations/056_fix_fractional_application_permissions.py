#!/usr/bin/env python3
"""
Migration 056: Grant DML privileges on fractional_application to the app user.

ROOT CAUSE
----------
Deleting a User via the admin panel raises:
    psycopg2.errors.InsufficientPrivilege: permission denied for table fractional_application

The table was created by the postgres superuser, so the app database user
(e.g. gighala_app) has no DELETE (or SELECT) privilege on it.  The admin
delete route explicitly deletes related fractional_application rows before
deleting the user, which requires at minimum SELECT + DELETE.

FIX
---
GRANT SELECT, INSERT, UPDATE, DELETE on fractional_application to the app user.
This migration does exactly that.

Usage
-----
  # With superuser URL (required if app user is not the table owner):
  SUPERUSER_DATABASE_URL="postgresql://postgres:secret@host/db" \\
      python migrations/056_fix_fractional_application_permissions.py

  # Or simply run against DATABASE_URL if the app user already owns the table:
  python migrations/056_fix_fractional_application_permissions.py

  # Or run these statements manually in psql as a superuser:
  GRANT SELECT, INSERT, UPDATE, DELETE ON fractional_application TO "<app_user>";
"""

import os
import sys
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text


def normalise_url(url):
    if url.startswith('postgres://'):
        return url.replace('postgres://', 'postgresql://', 1)
    return url


def run_migration():
    database_url = os.environ.get('DATABASE_URL', '')
    superuser_url = os.environ.get('SUPERUSER_DATABASE_URL', '') or database_url

    if not database_url:
        print('ERROR: DATABASE_URL environment variable is not set.')
        return False

    is_postgres = 'postgresql' in database_url or 'postgres' in database_url

    print('=' * 65)
    print('Migration 056: Fix fractional_application permissions')
    print('=' * 65)

    if not is_postgres:
        print('Database type: SQLite – no role-based permissions, nothing to do.')
        return True

    app_user = urlparse(database_url).username or ''
    if not app_user:
        print('ERROR: Could not extract username from DATABASE_URL.')
        return False

    grant_url = normalise_url(superuser_url)
    grant_user = urlparse(grant_url).username or ''

    print(f'Application DB user : {app_user}')
    if grant_user and grant_user != app_user:
        print(f'Granting via        : {grant_user} (superuser URL)')
    print()

    statements = [
        f'GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE fractional_application TO "{app_user}"',
    ]

    engine = create_engine(grant_url)
    errors = 0

    with engine.connect() as conn:
        for stmt in statements:
            try:
                conn.execute(text(stmt))
                conn.commit()
                print(f'[OK]   {stmt}')
            except Exception as e:
                err = str(e).lower()
                if 'already' in err and 'privilege' in err:
                    print(f'[SKIP] already granted')
                    conn.rollback()
                elif 'does not exist' in err:
                    print(f'[SKIP] table does not exist yet – will be created on next app start')
                    conn.rollback()
                else:
                    errors += 1
                    print(f'[ERROR] {stmt}')
                    print(f'        {e}')
                    conn.rollback()

    print()
    if errors:
        print('Migration 056 completed WITH ERRORS.')
        print()
        print('The connecting user lacks the privilege to grant on this table.')
        print('Retry with a superuser connection:')
        print()
        print('  SUPERUSER_DATABASE_URL="postgresql://postgres:secret@host/db" \\')
        print('      python migrations/056_fix_fractional_application_permissions.py')
        print()
        print('Or run this in psql as a superuser:')
        print()
        print(f'  GRANT SELECT, INSERT, UPDATE, DELETE ON fractional_application TO "{app_user}";')
        return False

    print('Migration 056 completed successfully.')
    return True


if __name__ == '__main__':
    success = run_migration()
    sys.exit(0 if success else 1)
