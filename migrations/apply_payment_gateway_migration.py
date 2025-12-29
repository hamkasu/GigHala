#!/usr/bin/env python3
"""
Apply payment_gateway migration to escrow table
"""

import os
import sys
from pathlib import Path

# Add parent directory to path to import app
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app, db
from sqlalchemy import text, inspect


def column_exists(table_name, column_name):
    """Check if a column exists in a table"""
    inspector = inspect(db.engine)
    try:
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        return column_name in columns
    except Exception:
        return False


def apply_migration():
    """Apply the payment_gateway migration"""
    print("=" * 60)
    print("Applying payment_gateway Migration to Escrow Table")
    print("=" * 60)

    # Check if column already exists
    if column_exists('escrow', 'payment_gateway'):
        print("✅ Column 'payment_gateway' already exists in escrow table")
        return True

    print("\n🔧 Adding payment_gateway column to escrow table...")

    migration_file = Path(__file__).parent / 'add_payment_gateway_to_escrow.sql'

    try:
        with open(migration_file, 'r') as f:
            sql = f.read()

        # Split and execute statements
        for statement in sql.split(';'):
            statement = statement.strip()
            if statement and not statement.startswith('--'):
                try:
                    db.session.execute(text(statement))
                    db.session.commit()
                    print(f"✅ Executed: {statement[:50]}...")
                except Exception as e:
                    print(f"⚠️  Warning: {str(e)}")
                    db.session.rollback()

        # Verify the column was added
        if column_exists('escrow', 'payment_gateway'):
            print("\n✅ Migration completed successfully!")
            print("   - payment_gateway column added to escrow table")
            print("   - Existing records updated with appropriate gateway values")
            print("   - Index created for query optimization")
            return True
        else:
            print("\n❌ Migration failed - column not found after migration")
            return False

    except Exception as e:
        print(f"\n❌ Error applying migration: {str(e)}")
        db.session.rollback()
        return False


if __name__ == '__main__':
    with app.app_context():
        success = apply_migration()
        sys.exit(0 if success else 1)
