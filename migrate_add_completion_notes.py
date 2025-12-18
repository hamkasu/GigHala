#!/usr/bin/env python3
"""
Database migration script to add completion_notes column to application table
"""
from app import app, db
from sqlalchemy import text

def migrate():
    with app.app_context():
        try:
            print("Starting migration...")

            # Check if column already exists
            result = db.session.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='application' AND column_name='completion_notes'"
            ))

            if result.fetchone():
                print("⚠️  Column 'completion_notes' already exists. Skipping column creation.")
            else:
                # Add completion_notes column
                db.session.execute(text('ALTER TABLE "application" ADD COLUMN completion_notes TEXT'))
                db.session.commit()
                print("✅ Added completion_notes column to application table")

            # Verify migration
            result = db.session.execute(text(
                "SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_name='application' AND column_name='completion_notes'"
            ))
            column_info = result.fetchone()

            if column_info:
                print(f"\n📊 Column details:")
                print(f"   - Name: {column_info[0]}")
                print(f"   - Type: {column_info[1]}")

            print("\n✅ Migration completed successfully!")
            return True

        except Exception as e:
            print(f"❌ Migration failed: {e}")
            db.session.rollback()
            return False

if __name__ == '__main__':
    success = migrate()
    exit(0 if success else 1)
