#!/usr/bin/env python3
"""
Database Migration Script for Password Reset Fields
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


def column_exists(table_name, column_name):
    """Check if a column exists in a table"""
    inspector = inspect(db.engine)
    try:
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        return column_name in columns
    except Exception:
        return False


def run_postgresql_migration():
    """Run PostgreSQL-specific migration"""
    print("🔧 Running PostgreSQL migration...")

    migration_file = Path(__file__).parent / '013_add_password_reset.sql'
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
                    # Ignore errors if columns already exist
                    if 'already exists' in str(e).lower():
                        print(f"⚠️  Column already exists, skipping: {str(e)}")
                    else:
                        print(f"⚠️  Warning: {str(e)}")
                    db.session.rollback()

        print("✅ PostgreSQL migration completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Error running PostgreSQL migration: {str(e)}")
        db.session.rollback()
        return False


def run_sqlite_migration():
    """Run SQLite-specific migration"""
    print("🔧 Running SQLite migration...")

    migration_file = Path(__file__).parent / '013_add_password_reset_sqlite.sql'
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
                    # Ignore errors if columns already exist
                    if 'duplicate column' in str(e).lower():
                        print(f"⚠️  Column already exists, skipping: {str(e)}")
                    else:
                        print(f"⚠️  Warning: {str(e)}")
                    db.session.rollback()

        print("✅ SQLite migration completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Error running SQLite migration: {str(e)}")
        db.session.rollback()
        return False


def verify_migration():
    """Verify that all required columns exist"""
    print("\n🔍 Verifying migration...")

    required_columns = {
        'user': ['password_reset_token', 'password_reset_expires']
    }

    all_good = True

    for table, columns in required_columns.items():
        for column in columns:
            if not column_exists(table, column):
                print(f"❌ Column '{table}.{column}' is missing")
                all_good = False
            else:
                print(f"✅ Column '{table}.{column}' exists")

    return all_good


def main():
    """Main migration entry point"""
    print("=" * 60)
    print("GigHala Password Reset Fields Migration")
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
        print("   - password_reset_token column added to user table")
        print("   - password_reset_expires column added to user table")
        print("   - Index created on password_reset_token for faster lookups")
        print("\n🚀 Your database is ready for password reset functionality!")
        return 0
    else:
        print("\n⚠️  Migration completed with warnings. Some columns may be missing.")
        return 1


if __name__ == '__main__':
    with app.app_context():
        exit_code = main()
        sys.exit(exit_code)
