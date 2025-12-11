#!/usr/bin/env python3
"""
Database migration script to add is_admin column to user table
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
                "WHERE table_name='user' AND column_name='is_admin'"
            ))

            if result.fetchone():
                print("⚠️  Column 'is_admin' already exists. Skipping column creation.")
            else:
                # Add is_admin column
                db.session.execute(text('ALTER TABLE "user" ADD COLUMN is_admin BOOLEAN DEFAULT FALSE'))
                db.session.commit()
                print("✅ Added is_admin column to user table")

            # Update admin user if exists
            result = db.session.execute(text("SELECT id FROM \"user\" WHERE email = 'admin@gighalal.com'"))
            admin_user = result.fetchone()

            if admin_user:
                db.session.execute(text("UPDATE \"user\" SET is_admin = TRUE WHERE email = 'admin@gighalal.com'"))
                db.session.commit()
                print("✅ Updated admin user (admin@gighalal.com) with admin privileges")
            else:
                print("⚠️  Admin user (admin@gighalal.com) not found. Will be created on next app start.")

            # Verify migration
            result = db.session.execute(text("SELECT username, email, is_admin FROM \"user\" WHERE is_admin = TRUE"))
            admins = result.fetchall()

            print(f"\n📊 Admin users in database: {len(admins)}")
            for admin in admins:
                print(f"   - {admin[0]} ({admin[1]})")

            print("\n✅ Migration completed successfully!")
            return True

        except Exception as e:
            print(f"❌ Migration failed: {e}")
            db.session.rollback()
            return False

if __name__ == '__main__':
    success = migrate()
    exit(0 if success else 1)
