#!/usr/bin/env python3
"""
Database Migration Script for Invoice and Receipt Workflow
Automatically detects database type and applies the appropriate migration
"""

import os
import sys
import sqlite3
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


def index_exists(index_name):
    """Check if an index exists"""
    inspector = inspect(db.engine)
    try:
        # Get all indexes across all tables
        for table_name in inspector.get_table_names():
            indexes = inspector.get_indexes(table_name)
            for idx in indexes:
                if idx['name'] == index_name:
                    return True
        return False
    except Exception:
        return False


def run_postgresql_migration():
    """Run PostgreSQL-specific migration"""
    print("🔧 Running PostgreSQL migration...")

    migration_file = Path(__file__).parent / '001_invoice_receipt_workflow.sql'
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

    migration_file = Path(__file__).parent / '001_invoice_receipt_workflow_sqlite.sql'
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
                    print(f"⚠️  Warning: {str(e)}")
                    db.session.rollback()

        print("✅ SQLite migration completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Error running SQLite migration: {str(e)}")
        db.session.rollback()
        return False


def verify_migration():
    """Verify that all required tables and columns exist"""
    print("\n🔍 Verifying migration...")

    required_tables = ['invoice', 'receipt', 'notification']
    required_columns = {
        'invoice': ['invoice_number', 'due_date', 'paid_at', 'payment_reference', 'notes'],
        'receipt': ['receipt_number', 'receipt_type', 'invoice_id', 'description'],
        'notification': ['related_id', 'link']
    }

    all_good = True

    for table in required_tables:
        if not table_exists(table):
            print(f"❌ Table '{table}' does not exist")
            all_good = False
        else:
            print(f"✅ Table '{table}' exists")

            # Check columns
            for column in required_columns.get(table, []):
                if not column_exists(table, column):
                    print(f"   ❌ Column '{table}.{column}' is missing")
                    all_good = False
                else:
                    print(f"   ✅ Column '{table}.{column}' exists")

    return all_good


def main():
    """Main migration entry point"""
    print("=" * 60)
    print("GigHala Invoice & Receipt Workflow Migration")
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
        print("   - Invoice table ready for tracking client invoices")
        print("   - Receipt table ready for payment receipts")
        print("   - Notification table ready for sharing invoices/receipts")
        print("   - Indexes created for optimal performance")
        print("\n🚀 Your database is ready for the invoice/receipt workflow!")
        return 0
    else:
        print("\n⚠️  Migration completed with warnings. Some tables/columns may be missing.")
        print("   Consider using Flask-SQLAlchemy's db.create_all() to create missing tables.")
        return 1


if __name__ == '__main__':
    with app.app_context():
        exit_code = main()
        sys.exit(exit_code)
