#!/usr/bin/env python3
"""
Apply DuitNow QR payment fields migration to escrow table
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
    """Apply the DuitNow fields migration"""
    print("=" * 60)
    print("Applying DuitNow Migration to Escrow Table")
    print("=" * 60)

    # Check which columns already exist
    columns_to_add = [
        ('payment_method', 'VARCHAR(30) DEFAULT "bank_transfer"'),
        ('qr_code_image', 'LONGBLOB'),
        ('qr_code_string', 'TEXT'),
        ('duitnow_reference', 'VARCHAR(50)'),
        ('payment_confirmation_ref', 'VARCHAR(100)'),
    ]

    existing_columns = []
    missing_columns = []

    for col_name, col_type in columns_to_add:
        if column_exists('escrow', col_name):
            print(f"✅ Column '{col_name}' already exists")
            existing_columns.append(col_name)
        else:
            missing_columns.append((col_name, col_type))

    if not missing_columns:
        print("\n✅ All DuitNow columns already exist in escrow table")
        return True

    print(f"\n🔧 Adding {len(missing_columns)} new columns to escrow table...")

    migration_file = Path(__file__).parent / 'add_duitnow_fields_to_escrow.sql'

    try:
        with open(migration_file, 'r') as f:
            sql_content = f.read()

        # Split and execute statements
        for statement in sql_content.split(';'):
            statement = statement.strip()
            if statement and not statement.startswith('--'):
                try:
                    db.session.execute(text(statement))
                    db.session.commit()
                    print(f"✅ Executed: {statement[:60]}...")
                except Exception as e:
                    print(f"⚠️  Warning: {str(e)}")
                    db.session.rollback()

        # Verify all columns were added
        all_added = all(column_exists('escrow', col_name) for col_name, _ in missing_columns)

        if all_added:
            print("\n✅ Migration completed successfully!")
            print("   - Added payment_method column")
            print("   - Added qr_code_image column for QR PNG bytes")
            print("   - Added qr_code_string column for EMVCo format")
            print("   - Added duitnow_reference column for DuitNow reference")
            print("   - Added payment_confirmation_ref column for bank transaction ref")
            print("   - Created indexes for DuitNow lookups")
            return True
        else:
            print("\n❌ Migration partially failed - some columns not found after migration")
            return False

    except FileNotFoundError:
        print(f"\n❌ Migration SQL file not found: {migration_file}")
        return False
    except Exception as e:
        print(f"\n❌ Error applying migration: {str(e)}")
        db.session.rollback()
        return False


if __name__ == '__main__':
    with app.app_context():
        success = apply_migration()
        sys.exit(0 if success else 1)
