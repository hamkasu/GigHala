#!/usr/bin/env python3
"""
Database migration script to add admin_role and admin_permissions columns to user table
"""
from app import app, db
from sqlalchemy import text

def migrate():
    with app.app_context():
        try:
            print("Starting migration for admin roles...")

            # Check if admin_role column already exists
            result = db.session.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='user' AND column_name='admin_role'"
            ))

            if result.fetchone():
                print("⚠️  Column 'admin_role' already exists. Skipping column creation.")
            else:
                # Add admin_role column
                db.session.execute(text('ALTER TABLE "user" ADD COLUMN admin_role VARCHAR(50)'))
                db.session.commit()
                print("✅ Added admin_role column to user table")

            # Check if admin_permissions column already exists
            result = db.session.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='user' AND column_name='admin_permissions'"
            ))

            if result.fetchone():
                print("⚠️  Column 'admin_permissions' already exists. Skipping column creation.")
            else:
                # Add admin_permissions column
                db.session.execute(text('ALTER TABLE "user" ADD COLUMN admin_permissions TEXT'))
                db.session.commit()
                print("✅ Added admin_permissions column to user table")

            # Update existing admin users to have 'super_admin' role
            result = db.session.execute(text(
                "UPDATE \"user\" SET admin_role = 'super_admin', admin_permissions = '[\"*\"]' WHERE is_admin = TRUE AND (admin_role IS NULL OR admin_role = '')"
            ))
            db.session.commit()
            updated_count = result.rowcount

            if updated_count > 0:
                print(f"✅ Updated {updated_count} existing admin user(s) with 'super_admin' role")
            else:
                print("ℹ️  No admin users needed updating")

            # Verify migration
            result = db.session.execute(text(
                "SELECT username, email, is_admin, admin_role FROM \"user\" WHERE is_admin = TRUE"
            ))
            admins = result.fetchall()

            print(f"\n📊 Admin users in database: {len(admins)}")
            for admin in admins:
                role = admin[3] if admin[3] else 'none'
                print(f"   - {admin[0]} ({admin[1]}) - Role: {role}")

            print("\n✅ Migration completed successfully!")
            return True

        except Exception as e:
            print(f"❌ Migration failed: {e}")
            db.session.rollback()
            return False

if __name__ == '__main__':
    success = migrate()
    exit(0 if success else 1)
