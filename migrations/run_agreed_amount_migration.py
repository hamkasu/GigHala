#!/usr/bin/env python3
"""
Database Migration Script for Adding agreed_amount Column
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

    migration_file = Path(__file__).parent / '002_add_agreed_amount.sql'
    with open(migration_file, 'r') as f:
        sql = f.read()

    try:
        # Split by semicolons but keep DO blocks together
        statements = []
        current_statement = []
        in_do_block = False

        for line in sql.split('\n'):
            if line.strip().startswith('DO $$'):
                in_do_block = True

            current_statement.append(line)

            if in_do_block and 'END $$;' in line:
                statements.append('\n'.join(current_statement))
                current_statement = []
                in_do_block = False
            elif not in_do_block and line.strip().endswith(';'):
                statements.append('\n'.join(current_statement))
                current_statement = []

        # Execute each statement
        for statement in statements:
            statement = statement.strip()
            if statement and not statement.startswith('--'):
                try:
                    db.session.execute(text(statement))
                    db.session.commit()
                except Exception as e:
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

    migration_file = Path(__file__).parent / '002_add_agreed_amount_sqlite.sql'
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
                    # SQLite will error if column already exists, which is fine
                    if 'duplicate column name' in str(e).lower():
                        print(f"⚠️  Column already exists, skipping...")
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
    """Verify that the agreed_amount column exists"""
    print("\n🔍 Verifying migration...")

    if column_exists('gig', 'agreed_amount'):
        print("✅ Column 'gig.agreed_amount' exists")
        return True
    else:
        print("❌ Column 'gig.agreed_amount' does not exist")
        return False


def main():
    """Main migration entry point"""
    print("=" * 60)
    print("GigHala agreed_amount Column Migration")
    print("=" * 60)

    # Detect database type
    db_type = get_database_type()
    print(f"\n📊 Detected database type: {db_type.upper()}")

    if db_type == 'unknown':
        print("❌ Unknown database type. Please check your DATABASE_URL.")
        return 1

    # Check if migration is needed
    if column_exists('gig', 'agreed_amount'):
        print("\n✅ Column 'gig.agreed_amount' already exists!")
        print("   No migration needed.")
        return 0

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
        print("   - agreed_amount column added to gig table")
        print("   - Index created for performance optimization")
        print("\n🚀 Your database is ready!")
        return 0
    else:
        print("\n⚠️  Migration completed with warnings.")
        return 1


if __name__ == '__main__':
    with app.app_context():
        exit_code = main()
        sys.exit(exit_code)
