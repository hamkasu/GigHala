#!/usr/bin/env python3
"""
Migration 052: Reassign worker_specialization / worker_rate_audit ownership
to the application database user.

This is the most reliable fix when migration 051 failed because the connecting
user was neither a superuser nor the table owner.

Strategy (tried in order, first success wins):
  A. ALTER TABLE … OWNER TO current_user (requires superuser privilege).
  B. SET ROLE <table_owner>; GRANT ALL … TO <app_user>; RESET ROLE
     (requires the app user to be a member of the table-owner role — common
     in Railway, Neon and Supabase managed Postgres setups).
  C. Print the exact SQL for a DBA to run manually.

Usage:
  # Using the app DATABASE_URL (may be enough on Railway/Neon):
  python migrations/052_reassign_specialization_ownership.py

  # Supply a superuser URL for strategy A:
  SUPERUSER_DATABASE_URL="postgresql://postgres:secret@host/db" \\
  python migrations/052_reassign_specialization_ownership.py
"""

import os
import sys
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy import create_engine, text


def _norm(url: str) -> str:
    return url.replace('postgres://', 'postgresql://', 1) if url.startswith('postgres://') else url


def run():
    db_url = os.environ.get('DATABASE_URL', '')
    su_url = os.environ.get('SUPERUSER_DATABASE_URL', '') or db_url

    if not db_url:
        print('ERROR: DATABASE_URL is not set.')
        return False

    if 'sqlite' in db_url:
        print('SQLite detected – no role-based permissions, nothing to do.')
        return True

    app_user = urlparse(db_url).username or ''
    print('=' * 60)
    print('Migration 052: Reassign specialization table ownership')
    print('=' * 60)
    print(f'App DB user : {app_user or "(unknown)"}')
    print()

    tables = ('worker_specialization', 'worker_rate_audit')
    sequences = ('worker_specialization_id_seq', 'worker_rate_audit_id_seq')

    # ------------------------------------------------------------------ #
    # Strategy A – use SUPERUSER_DATABASE_URL (or the app URL if it has  #
    # superuser privileges) to ALTER TABLE OWNER.                         #
    # ------------------------------------------------------------------ #
    print('[Strategy A] ALTER TABLE OWNER via superuser URL …')
    try:
        engine = create_engine(_norm(su_url))
        with engine.connect() as conn:
            su_user = conn.execute(text('SELECT current_user')).scalar()
            print(f'  Connected as: {su_user}')
            for tbl in tables:
                tgt = app_user or su_user
                conn.execute(text(f'ALTER TABLE {tbl} OWNER TO "{tgt}"'))
                conn.commit()
                print(f'  [OK] ALTER TABLE {tbl} OWNER TO "{tgt}"')
            for seq in sequences:
                try:
                    tgt = app_user or su_user
                    conn.execute(text(f'ALTER SEQUENCE {seq} OWNER TO "{tgt}"'))
                    conn.commit()
                    print(f'  [OK] ALTER SEQUENCE {seq} OWNER TO "{tgt}"')
                except Exception:
                    conn.rollback()
        print()
        print('Strategy A succeeded!')
        return True
    except Exception as e:
        print(f'  Strategy A failed: {e}')
        print()

    # ------------------------------------------------------------------ #
    # Strategy B – SET ROLE to the current table owner, then GRANT.      #
    # Works when the app user is a *member* of the table-owner role.     #
    # ------------------------------------------------------------------ #
    print('[Strategy B] SET ROLE to table owner, then GRANT …')
    try:
        engine = create_engine(_norm(db_url))
        with engine.connect() as conn:
            row = conn.execute(text(
                "SELECT tableowner FROM pg_tables WHERE tablename = 'worker_specialization'"
            )).fetchone()
            if not row:
                print('  worker_specialization table not found – has migration 050 run?')
                print()
            else:
                owner = row[0]
                current = conn.execute(text('SELECT current_user')).scalar()
                print(f'  Table owner  : {owner}')
                print(f'  Current user : {current}')

                conn.execute(text(f'SET ROLE "{owner}"'))
                for tbl in tables:
                    conn.execute(text(f'GRANT ALL ON TABLE {tbl} TO "{app_user}"'))
                    print(f'  [OK] GRANT ALL ON TABLE {tbl} TO "{app_user}"')
                for seq in sequences:
                    try:
                        conn.execute(text(f'GRANT ALL ON SEQUENCE {seq} TO "{app_user}"'))
                        print(f'  [OK] GRANT ALL ON SEQUENCE {seq} TO "{app_user}"')
                    except Exception:
                        pass
                conn.execute(text('RESET ROLE'))
                conn.commit()
                print()
                print('Strategy B succeeded!')
                return True
    except Exception as e:
        print(f'  Strategy B failed: {e}')
        print()

    # ------------------------------------------------------------------ #
    # Strategy C – nothing worked; print exact SQL for manual execution. #
    # ------------------------------------------------------------------ #
    fix_user = app_user or '<your_app_db_user>'
    print('=' * 60)
    print('All automatic strategies failed.')
    print('Connect to your database as a superuser and run:')
    print()
    print(f'  ALTER TABLE worker_specialization OWNER TO "{fix_user}";')
    print(f'  ALTER TABLE worker_rate_audit OWNER TO "{fix_user}";')
    print()
    print('Or, if you prefer GRANT instead of ownership transfer:')
    print()
    print(f'  GRANT ALL ON TABLE worker_specialization TO "{fix_user}";')
    print(f'  GRANT ALL ON TABLE worker_rate_audit TO "{fix_user}";')
    print(f'  GRANT ALL ON SEQUENCE worker_specialization_id_seq TO "{fix_user}";')
    print(f'  GRANT ALL ON SEQUENCE worker_rate_audit_id_seq TO "{fix_user}";')
    print()
    print('On Railway: open the Postgres service → Data tab → Query, paste the SQL above.')
    print('On Neon: open the Neon dashboard → SQL Editor, paste the SQL above.')
    print('On Supabase: open the Supabase dashboard → SQL Editor, paste the SQL above.')
    print('=' * 60)
    return False


def verify():
    db_url = os.environ.get('DATABASE_URL', '')
    if not db_url or 'sqlite' in db_url:
        return
    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)

    print()
    print('Verifying …')
    engine = create_engine(db_url)
    for tbl in ('worker_specialization', 'worker_rate_audit'):
        try:
            with engine.connect() as conn:
                conn.execute(text(f'SELECT COUNT(*) FROM {tbl}'))
            print(f'  [OK]   SELECT on {tbl}')
        except Exception as e:
            print(f'  [FAIL] SELECT on {tbl}: {e}')


if __name__ == '__main__':
    ok = run()
    if ok:
        verify()
    sys.exit(0 if ok else 1)
