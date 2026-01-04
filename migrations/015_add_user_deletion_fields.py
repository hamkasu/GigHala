#!/usr/bin/env python3
"""
Database Migration Script to Add User Deletion Fields

Adds soft delete functionality to User model:
- is_deleted (Boolean): Tracks if user has been soft deleted
- deleted_at (DateTime): Timestamp of when user was deleted
"""

import sys
from pathlib import Path

# Add parent directory to path to import app
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app, db
from sqlalchemy import text

def add_user_deletion_fields():
    """Add is_deleted and deleted_at columns to user table"""
    print("\n📦 Adding user deletion fields...")
    print("-" * 60)

    try:
        # Check if columns already exist
        with db.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='user' AND column_name IN ('is_deleted', 'deleted_at')
            """))
            existing_columns = [row[0] for row in result]

        if 'is_deleted' in existing_columns and 'deleted_at' in existing_columns:
            print("ℹ️  Columns already exist - skipping migration")
            return True

        # Add is_deleted column if it doesn't exist
        if 'is_deleted' not in existing_columns:
            print("\n➕ Adding 'is_deleted' column...")
            with db.engine.connect() as conn:
                conn.execute(text("""
                    ALTER TABLE user
                    ADD COLUMN is_deleted BOOLEAN DEFAULT FALSE
                """))
                conn.commit()
            print("✅ Added 'is_deleted' column")

        # Add deleted_at column if it doesn't exist
        if 'deleted_at' not in existing_columns:
            print("\n➕ Adding 'deleted_at' column...")
            with db.engine.connect() as conn:
                conn.execute(text("""
                    ALTER TABLE user
                    ADD COLUMN deleted_at TIMESTAMP
                """))
                conn.commit()
            print("✅ Added 'deleted_at' column")

        print("\n" + "-" * 60)
        print("✅ Successfully added user deletion fields")
        return True

    except Exception as e:
        print(f"\n❌ Error adding columns: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main migration entry point"""
    print("=" * 60)
    print("GigHala User Deletion Fields Migration")
    print("=" * 60)

    try:
        success = add_user_deletion_fields()

        if success:
            print("\n✅ Migration completed successfully!")
            print("\n📝 Summary:")
            print("   This migration adds soft delete functionality to users.")
            print("   Users can now be 'deleted' by anonymizing their data")
            print("   instead of actual deletion from the database.")
            print("\n🚀 User deletion feature is now available!")
            return 0
        else:
            print("\n❌ Migration failed!")
            return 1

    except Exception as e:
        print(f"\n❌ Migration failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    with app.app_context():
        exit_code = main()
        sys.exit(exit_code)
