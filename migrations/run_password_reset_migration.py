#!/usr/bin/env python3
"""
Database Migration Script for Password Reset Fields
Automatically detects database type and applies the appropriate migration
"""

import os
import sys
from pathlib import Path
from urllib.parse import urlparse

def get_database_url():
    """Get the database URL from environment"""
    return os.environ.get('DATABASE_URL', 'sqlite:///gighala.db')

def get_database_type():
    """Detect the database type from the connection string"""
    db_uri = get_database_url()
    if db_uri.startswith('sqlite'):
        return 'sqlite'
    elif 'postgres' in db_uri:
        return 'postgresql'
    else:
        return 'unknown'

def get_db_connection():
    """Get a database connection based on the database type"""
    db_type = get_database_type()
    db_uri = get_database_url()

    if db_type == 'postgresql':
        import psycopg2
        # Handle both postgres:// and postgresql:// schemes
        if db_uri.startswith('postgres://'):
            db_uri = db_uri.replace('postgres://', 'postgresql://', 1)

        result = urlparse(db_uri)
        conn = psycopg2.connect(
            database=result.path[1:],
            user=result.username,
            password=result.password,
            host=result.hostname,
            port=result.port
        )
        return conn, db_type
    elif db_type == 'sqlite':
        import sqlite3
        db_path = db_uri.replace('sqlite:///', '')
        conn = sqlite3.connect(db_path)
        return conn, db_type
    else:
        return None, db_type

def column_exists(cursor, table_name, column_name, db_type):
    """Check if a column exists in a table"""
    try:
        if db_type == 'postgresql':
            cursor.execute("""
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = %s
                    AND column_name = %s
                )
            """, (table_name, column_name))
            return cursor.fetchone()[0]
        elif db_type == 'sqlite':
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [row[1] for row in cursor.fetchall()]
            return column_name in columns
    except Exception:
        return False


def run_postgresql_migration(conn):
    """Run PostgreSQL-specific migration"""
    print("🔧 Running PostgreSQL migration...")

    migration_file = Path(__file__).parent / '013_add_password_reset.sql'
    with open(migration_file, 'r') as f:
        sql = f.read()

    cursor = conn.cursor()
    try:
        # Split and execute statements
        for statement in sql.split(';'):
            statement = statement.strip()
            if statement and not statement.startswith('--'):
                try:
                    cursor.execute(statement)
                    conn.commit()
                except Exception as e:
                    # Ignore errors if columns already exist
                    if 'already exists' in str(e).lower():
                        print(f"⚠️  Column already exists, skipping")
                    else:
                        print(f"⚠️  Warning: {str(e)}")
                    conn.rollback()

        print("✅ PostgreSQL migration completed successfully!")
        cursor.close()
        return True

    except Exception as e:
        print(f"❌ Error running PostgreSQL migration: {str(e)}")
        conn.rollback()
        cursor.close()
        return False


def run_sqlite_migration(conn):
    """Run SQLite-specific migration"""
    print("🔧 Running SQLite migration...")

    migration_file = Path(__file__).parent / '013_add_password_reset_sqlite.sql'
    with open(migration_file, 'r') as f:
        sql = f.read()

    cursor = conn.cursor()
    try:
        # Split and execute statements
        for statement in sql.split(';'):
            statement = statement.strip()
            if statement and not statement.startswith('--'):
                try:
                    cursor.execute(statement)
                    conn.commit()
                except Exception as e:
                    # Ignore errors if columns already exist
                    if 'duplicate column' in str(e).lower():
                        print(f"⚠️  Column already exists, skipping")
                    else:
                        print(f"⚠️  Warning: {str(e)}")
                    conn.rollback()

        print("✅ SQLite migration completed successfully!")
        cursor.close()
        return True

    except Exception as e:
        print(f"❌ Error running SQLite migration: {str(e)}")
        conn.rollback()
        cursor.close()
        return False


def verify_migration(cursor, db_type):
    """Verify that all required columns exist"""
    print("\n🔍 Verifying migration...")

    required_columns = {
        'user': ['password_reset_token', 'password_reset_expires']
    }

    all_good = True

    for table, columns in required_columns.items():
        for column in columns:
            if not column_exists(cursor, table, column, db_type):
                print(f"❌ Column '{table}.{column}' is missing")
                all_good = False
            else:
                print(f"✅ Column '{table}.{column}' exists")

    return all_good


def main():
    """Main migration entry point"""
    print("=" * 60)
    print("GigHala Password Reset Fields Migration")
    print("=" * 60)

    # Detect database type
    db_type = get_database_type()
    print(f"\n📊 Detected database type: {db_type.upper()}")

    if db_type == 'unknown':
        print("❌ Unknown database type. Please check your DATABASE_URL.")
        return 1

    # Get database connection
    try:
        conn, db_type = get_db_connection()
        if conn is None:
            print("❌ Could not connect to database.")
            return 1
        print(f"✅ Connected to {db_type} database")
    except Exception as e:
        print(f"❌ Error connecting to database: {str(e)}")
        return 1

    # Run appropriate migration
    success = False
    try:
        if db_type == 'postgresql':
            success = run_postgresql_migration(conn)
        elif db_type == 'sqlite':
            success = run_sqlite_migration(conn)

        if not success:
            print("\n❌ Migration failed!")
            return 1

        # Verify migration
        cursor = conn.cursor()
        if verify_migration(cursor, db_type):
            print("\n✅ Migration verified successfully!")
            print("\n📝 Summary:")
            print("   - password_reset_token column added to user table")
            print("   - password_reset_expires column added to user table")
            print("   - Index created on password_reset_token for faster lookups")
            print("\n🚀 Your database is ready for password reset functionality!")
            cursor.close()
            return 0
        else:
            print("\n⚠️  Migration completed with warnings. Some columns may be missing.")
            cursor.close()
            return 1
    finally:
        conn.close()


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
