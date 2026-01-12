#!/usr/bin/env python3
"""
Database Migration Script for Manual Payout Batch Release
Automatically detects database type and applies the appropriate migration
"""

import os
import sys
from pathlib import Path

# Add parent directory to path to import app
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app, db
from sqlalchemy import text, inspect


def get_database_type():
    """Detect the database type from the connection string"""
    db_uri = app.config['SQLALCHEMY_DATABASE_URI']
    if db_uri.startswith('sqlite'):
        return 'sqlite'
    elif 'postgres' in db_uri:
        return 'postgresql'
    else:
        return 'unknown'


def table_exists(table_name):
    """Check if a table exists in the database"""
    inspector = inspect(db.engine)
    return table_name in inspector.get_table_names()


def column_exists(table_name, column_name):
    """Check if a column exists in a table"""
    inspector = inspect(db.engine)
    if not table_exists(table_name):
        return False
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def run_postgresql_migration():
    """Run PostgreSQL-specific migration"""
    print("🔧 Running PostgreSQL migration...")

    migration_file = Path(__file__).parent / '015_add_manual_payout_batch_release.sql'
    with open(migration_file, 'r') as f:
        sql = f.read()

    try:
        # Split and execute statements
        for statement in sql.split(';'):
            statement = statement.strip()
            if statement and not statement.startswith('--'):
                try:
                    db.session.execute(text(statement))
                    db.session.commit()
                except Exception as e:
                    # Ignore "column already exists" errors
                    if 'already exists' in str(e).lower():
                        print(f"⚠️  Column/Index already exists, skipping...")
                        db.session.rollback()
                    else:
                        raise e

        print("✅ PostgreSQL migration completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Error running PostgreSQL migration: {str(e)}")
        db.session.rollback()
        return False


def run_sqlite_migration():
    """Run SQLite-specific migration"""
    print("🔧 Running SQLite migration...")

    migration_file = Path(__file__).parent / '015_add_manual_payout_batch_release_sqlite.sql'
    with open(migration_file, 'r') as f:
        sql = f.read()

    try:
        # Split and execute statements
        for statement in sql.split(';'):
            statement = statement.strip()
            if statement and not statement.startswith('--'):
                try:
                    db.session.execute(text(statement))
                    db.session.commit()
                except Exception as e:
                    # Ignore "duplicate column" errors
                    if 'duplicate column' in str(e).lower():
                        print(f"⚠️  Column already exists, skipping...")
                        db.session.rollback()
                    else:
                        raise e

        print("✅ SQLite migration completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Error running SQLite migration: {str(e)}")
        db.session.rollback()
        return False


def verify_migration():
    """Verify that all required columns exist"""
    print("\n🔍 Verifying migration...")

    required_columns = [
        'scheduled_release_time',
        'release_batch',
        'ready_for_release',
        'ready_for_release_at',
        'ready_for_release_by',
        'external_payment_confirmed',
        'external_payment_confirmed_at',
        'external_payment_confirmed_by'
    ]

    all_good = True

    if not table_exists('payout'):
        print(f"❌ Table 'payout' does not exist")
        return False

    print(f"✅ Table 'payout' exists")

    # Check columns
    for column in required_columns:
        if not column_exists('payout', column):
            print(f"   ❌ Column 'payout.{column}' is missing")
            all_good = False
        else:
            print(f"   ✅ Column 'payout.{column}' exists")

    return all_good


def main():
    """Main migration entry point"""
    print("=" * 60)
    print("GigHala Manual Payout Batch Release Migration")
    print("=" * 60)

    # Detect database type
    db_type = get_database_type()
    print(f"\n📊 Detected database type: {db_type.upper()}")

    if db_type == 'unknown':
        print("❌ Unknown database type. Please check your DATABASE_URL.")
        return 1

    # Run appropriate migration
    success = False
    if db_type == 'postgresql':
        success = run_postgresql_migration()
    elif db_type == 'sqlite':
        success = run_sqlite_migration()

    if not success:
        print("\n❌ Migration failed!")
        return 1

    # Verify migration
    if verify_migration():
        print("\n✅ Migration verified successfully!")
        print("\n📝 Summary:")
        print("   - scheduled_release_time: Batch release time (8am or 4pm)")
        print("   - release_batch: Batch identifier")
        print("   - ready_for_release: Admin marked ready")
        print("   - ready_for_release_at: Timestamp when marked ready")
        print("   - ready_for_release_by: Admin who marked ready")
        print("   - external_payment_confirmed: Payment confirmed")
        print("   - external_payment_confirmed_at: Timestamp when confirmed")
        print("   - external_payment_confirmed_by: Admin who confirmed")
        print("   - Indexes created for optimal performance")
        print("\n🚀 Your database is ready for manual payout batch release!")
        return 0
    else:
        print("\n⚠️  Migration completed with warnings. Some columns may be missing.")
        return 1


if __name__ == '__main__':
    with app.app_context():
        exit_code = main()
        sys.exit(exit_code)
