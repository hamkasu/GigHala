#!/usr/bin/env python3
"""
Database Migration Script for Stripe Connect Instant Payouts
Adds necessary fields to support Stripe Connect Express accounts for Malaysian freelancers
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


def column_exists(table_name, column_name):
    """Check if a column exists in a table"""
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    if table_name not in tables:
        return False
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def run_migration():
    """Run the Stripe Connect migration"""
    print("🔧 Running Stripe Connect migration...")

    migration_file = Path(__file__).parent / 'add_stripe_connect_fields.sql'
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
                    print(f"✅ Executed: {statement[:60]}...")
                except Exception as e:
                    print(f"⚠️  Warning: {str(e)}")
                    db.session.rollback()

        print("✅ Migration completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Error running migration: {str(e)}")
        db.session.rollback()
        return False


def verify_migration():
    """Verify that all required columns exist"""
    print("\n🔍 Verifying migration...")

    required_columns = {
        'user': [
            'stripe_account_id',
            'stripe_account_status',
            'stripe_onboarding_completed',
            'instant_payout_enabled',
            'stripe_account_created_at'
        ],
        'payout': [
            'is_instant',
            'stripe_payout_id',
            'estimated_arrival'
        ]
    }

    all_good = True

    for table, columns in required_columns.items():
        print(f"\n📋 Checking table '{table}':")
        for column in columns:
            if not column_exists(table, column):
                print(f"   ❌ Column '{table}.{column}' is missing")
                all_good = False
            else:
                print(f"   ✅ Column '{table}.{column}' exists")

    return all_good


def main():
    """Main migration entry point"""
    print("=" * 70)
    print("GigHala Stripe Connect Instant Payouts Migration")
    print("=" * 70)

    # Detect database type
    db_type = get_database_type()
    print(f"\n📊 Detected database type: {db_type.upper()}")

    if db_type == 'unknown':
        print("❌ Unknown database type. Please check your DATABASE_URL.")
        return 1

    # Run migration
    if not run_migration():
        print("\n❌ Migration failed!")
        return 1

    # Verify migration
    if verify_migration():
        print("\n✅ Migration verified successfully!")
        print("\n📝 Summary:")
        print("   - User table: Added Stripe Connect account fields")
        print("   - Payout table: Added instant payout tracking")
        print("   - Indexes created for optimal performance")
        print("\n🚀 Your database is ready for Stripe Instant Payouts!")
        return 0
    else:
        print("\n⚠️  Migration completed with warnings.")
        return 1


if __name__ == '__main__':
    with app.app_context():
        exit_code = main()
        sys.exit(exit_code)
