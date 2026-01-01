#!/usr/bin/env python3
"""
Simple Database Migration Script for Password Reset Fields
This script can be run directly with the DATABASE_URL environment variable
"""

import os
import sys
import psycopg2
from urllib.parse import urlparse

def get_db_connection():
    """Get database connection from DATABASE_URL environment variable"""
    database_url = os.environ.get('DATABASE_URL')

    if not database_url:
        print("❌ ERROR: DATABASE_URL environment variable is not set")
        print("Please set it using: export DATABASE_URL='postgresql://user:pass@host:port/dbname'")
        sys.exit(1)

    # Parse the database URL
    # Handle both postgres:// and postgresql:// schemes
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)

    try:
        result = urlparse(database_url)
        conn = psycopg2.connect(
            database=result.path[1:],
            user=result.username,
            password=result.password,
            host=result.hostname,
            port=result.port
        )
        return conn
    except Exception as e:
        print(f"❌ Error connecting to database: {str(e)}")
        sys.exit(1)

def column_exists(cursor, table_name, column_name):
    """Check if a column exists in a table"""
    cursor.execute("""
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = %s
            AND column_name = %s
        )
    """, (table_name, column_name))
    return cursor.fetchone()[0]

def run_migration(conn):
    """Run the migration"""
    cursor = conn.cursor()

    print("=" * 60)
    print("GigHala Password Reset Fields Migration")
    print("=" * 60)

    # Check current state
    print("\n🔍 Checking current database state...")

    has_token = column_exists(cursor, 'user', 'password_reset_token')
    has_expires = column_exists(cursor, 'user', 'password_reset_expires')

    if has_token and has_expires:
        print("✅ Columns already exist! No migration needed.")
        cursor.close()
        return

    print(f"   password_reset_token: {'✅ exists' if has_token else '❌ missing'}")
    print(f"   password_reset_expires: {'✅ exists' if has_expires else '❌ missing'}")

    # Run migration
    print("\n🔧 Running migration...")

    try:
        if not has_token:
            print("   Adding password_reset_token column...")
            cursor.execute('ALTER TABLE "user" ADD COLUMN password_reset_token VARCHAR(100);')
            print("   ✅ Added password_reset_token")

        if not has_expires:
            print("   Adding password_reset_expires column...")
            cursor.execute('ALTER TABLE "user" ADD COLUMN password_reset_expires TIMESTAMP;')
            print("   ✅ Added password_reset_expires")

        # Create index if it doesn't exist
        print("   Creating index on password_reset_token...")
        cursor.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM pg_indexes
                    WHERE indexname = 'idx_user_password_reset_token'
                ) THEN
                    CREATE INDEX idx_user_password_reset_token ON "user"(password_reset_token);
                END IF;
            END $$;
        """)
        print("   ✅ Index created")

        # Commit changes
        conn.commit()

        print("\n✅ Migration completed successfully!")
        print("\n📝 Summary:")
        print("   - password_reset_token column added to user table")
        print("   - password_reset_expires column added to user table")
        print("   - Index created on password_reset_token for faster lookups")
        print("\n🚀 Your database is ready for password reset functionality!")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error during migration: {str(e)}")
        sys.exit(1)
    finally:
        cursor.close()

def main():
    """Main entry point"""
    print("Connecting to database...")
    conn = get_db_connection()
    print("✅ Connected to database\n")

    try:
        run_migration(conn)
    finally:
        conn.close()
        print("\n🔌 Database connection closed")

if __name__ == '__main__':
    main()
