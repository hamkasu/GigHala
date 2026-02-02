#!/usr/bin/env python3
"""
Migration 050: Add Specialized Worker Rates

Run this script to add support for workers to define their own specific charges/rates.

Usage:
    python migrations/050_run_specialized_worker_rates_migration.py

This will:
1. Add rate fields to worker_specialization table
2. Add specialized rate tracking to gig_worker table
3. Add specialized rate reference to application table
4. Create audit table for rate changes (PDPA compliance)
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from sqlalchemy import text


def run_migration():
    """Run the specialized worker rates migration."""
    database_url = os.environ.get('DATABASE_URL', '')
    is_postgres = 'postgresql' in database_url or 'postgres' in database_url

    print("=" * 60)
    print("Migration 050: Add Specialized Worker Rates")
    print("=" * 60)
    print(f"Database type: {'PostgreSQL' if is_postgres else 'SQLite'}")
    print()

    with app.app_context():
        try:
            # Determine which SQL file to use
            migration_dir = os.path.dirname(os.path.abspath(__file__))
            if is_postgres:
                sql_file = os.path.join(migration_dir, '050_add_specialized_worker_rates.sql')
            else:
                sql_file = os.path.join(migration_dir, '050_add_specialized_worker_rates_sqlite.sql')

            print(f"Using migration file: {sql_file}")
            print()

            with open(sql_file, 'r') as f:
                sql_content = f.read()

            # Split SQL into individual statements
            statements = [s.strip() for s in sql_content.split(';') if s.strip() and not s.strip().startswith('--')]

            success_count = 0
            skip_count = 0
            error_count = 0

            for i, statement in enumerate(statements, 1):
                if not statement or statement.startswith('--'):
                    continue

                # Skip comments and verification queries
                if 'information_schema' in statement.lower():
                    continue
                if statement.upper().startswith('COMMIT'):
                    continue

                try:
                    db.session.execute(text(statement))
                    db.session.commit()
                    success_count += 1
                    print(f"[OK] Statement {i}: {statement[:60]}...")
                except Exception as e:
                    error_msg = str(e).lower()
                    # SQLite: "duplicate column name" or "already exists"
                    # PostgreSQL: "already exists" or "duplicate"
                    if 'already exists' in error_msg or 'duplicate' in error_msg:
                        skip_count += 1
                        print(f"[SKIP] Statement {i}: Column/table already exists")
                    else:
                        error_count += 1
                        print(f"[ERROR] Statement {i}: {e}")
                    db.session.rollback()

            print()
            print("=" * 60)
            print("Migration Summary")
            print("=" * 60)
            print(f"Successful: {success_count}")
            print(f"Skipped (already exists): {skip_count}")
            print(f"Errors: {error_count}")
            print()

            if error_count == 0:
                print("Migration completed successfully!")
                return True
            else:
                print("Migration completed with some errors. Please review above.")
                return False

        except Exception as e:
            print(f"Migration failed: {e}")
            db.session.rollback()
            return False


def verify_migration():
    """Verify that the migration was applied correctly."""
    print()
    print("=" * 60)
    print("Verifying Migration")
    print("=" * 60)

    with app.app_context():
        try:
            # Check worker_specialization columns
            result = db.session.execute(text("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'worker_specialization'
            """)).fetchall()
            columns = [row[0] for row in result]

            required_columns = ['specialization_title', 'base_hourly_rate', 'base_fixed_rate', 'premium_multiplier']
            for col in required_columns:
                if col in columns:
                    print(f"[OK] worker_specialization.{col} exists")
                else:
                    print(f"[MISSING] worker_specialization.{col}")

            # Check gig_worker columns
            result = db.session.execute(text("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'gig_worker'
            """)).fetchall()
            columns = [row[0] for row in result]

            required_columns = ['specialized_rate_used', 'specialization_id']
            for col in required_columns:
                if col in columns:
                    print(f"[OK] gig_worker.{col} exists")
                else:
                    print(f"[MISSING] gig_worker.{col}")

            # Check application columns
            result = db.session.execute(text("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'application'
            """)).fetchall()
            columns = [row[0] for row in result]

            required_columns = ['use_specialized_rate', 'specialization_id']
            for col in required_columns:
                if col in columns:
                    print(f"[OK] application.{col} exists")
                else:
                    print(f"[MISSING] application.{col}")

            # Check audit table
            result = db.session.execute(text("""
                SELECT table_name FROM information_schema.tables
                WHERE table_name = 'worker_rate_audit'
            """)).fetchall()

            if result:
                print("[OK] worker_rate_audit table exists")
            else:
                print("[MISSING] worker_rate_audit table")

            print()
            print("Verification complete!")

        except Exception as e:
            print(f"Verification error: {e}")


if __name__ == '__main__':
    success = run_migration()
    if success:
        verify_migration()
    sys.exit(0 if success else 1)
