#!/usr/bin/env python3
"""
Database migration script to add agreed_amount column to gig table
This column tracks the negotiated payment amount between client and freelancer
"""
from app import app, db
from sqlalchemy import text

def migrate():
    with app.app_context():
        try:
            print("Starting migration...")

            # Detect database type
            db_uri = app.config['SQLALCHEMY_DATABASE_URI']
            is_postgres = 'postgres' in db_uri.lower()
            is_sqlite = db_uri.startswith('sqlite')

            # Check if column already exists
            if is_postgres:
                result = db.session.execute(text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name='gig' AND column_name='agreed_amount'"
                ))
            elif is_sqlite:
                # For SQLite, use pragma
                result = db.session.execute(text("PRAGMA table_info(gig)"))
                columns = [row[1] for row in result.fetchall()]
                column_exists = 'agreed_amount' in columns
                result = None
            else:
                print("❌ Unknown database type")
                return False

            if is_postgres and result.fetchone():
                print("⚠️  Column 'agreed_amount' already exists. Skipping column creation.")
            elif is_sqlite and column_exists:
                print("⚠️  Column 'agreed_amount' already exists. Skipping column creation.")
            else:
                # Add agreed_amount column
                if is_postgres:
                    db.session.execute(text('ALTER TABLE gig ADD COLUMN agreed_amount NUMERIC(10, 2)'))
                elif is_sqlite:
                    db.session.execute(text('ALTER TABLE gig ADD COLUMN agreed_amount REAL'))

                db.session.commit()
                print("✅ Added agreed_amount column to gig table")

            # Verify migration
            if is_postgres:
                result = db.session.execute(text(
                    "SELECT column_name, data_type FROM information_schema.columns "
                    "WHERE table_name='gig' AND column_name='agreed_amount'"
                ))
                column_info = result.fetchone()

                if column_info:
                    print(f"\n📊 Column details:")
                    print(f"   - Name: {column_info[0]}")
                    print(f"   - Type: {column_info[1]}")
            elif is_sqlite:
                result = db.session.execute(text("PRAGMA table_info(gig)"))
                for row in result.fetchall():
                    if row[1] == 'agreed_amount':
                        print(f"\n📊 Column details:")
                        print(f"   - Name: {row[1]}")
                        print(f"   - Type: {row[2]}")

            print("\n✅ Migration completed successfully!")
            print("\n📝 Summary:")
            print("   - agreed_amount column added to gig table")
            print("   - This column tracks the negotiated payment amount")
            print("   - Column type: NUMERIC(10, 2) for PostgreSQL, REAL for SQLite")
            return True

        except Exception as e:
            print(f"❌ Migration failed: {e}")
            db.session.rollback()
            return False

if __name__ == '__main__':
    success = migrate()
    exit(0 if success else 1)
