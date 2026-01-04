#!/usr/bin/env python3
"""
Migration: Add AI Moderation Support
=====================================

This migration adds AI-powered halal compliance moderation to the Gig table.
It adds a new field to store structured AI moderation results from the Groq API.

Usage:
    python migrations/048_add_ai_moderation.py

Database Support:
    - PostgreSQL (primary)
    - SQLite (fallback)
"""

import os
import sys
from sqlalchemy import create_engine, text

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Get database URL from environment
DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    print("❌ ERROR: DATABASE_URL environment variable not set")
    print("Please set DATABASE_URL in your .env file or environment")
    sys.exit(1)

# Determine database type
is_postgres = DATABASE_URL.startswith('postgresql')
is_sqlite = DATABASE_URL.startswith('sqlite')

print("🔧 AI Moderation Migration")
print("="*60)
print(f"Database: {'PostgreSQL' if is_postgres else 'SQLite'}")
print(f"URL: {DATABASE_URL[:30]}...")
print("="*60)

# Create database engine
engine = create_engine(DATABASE_URL)

# Migration SQL for PostgreSQL
POSTGRES_MIGRATION = """
-- Add ai_moderation_result column to gig table
ALTER TABLE gig
ADD COLUMN IF NOT EXISTS ai_moderation_result TEXT;

-- Add index for querying gigs flagged for review
CREATE INDEX IF NOT EXISTS idx_gig_ai_moderation
ON gig ((ai_moderation_result::jsonb->>'action'));

-- Create a view for admin dashboard to see flagged gigs
CREATE OR REPLACE VIEW ai_flagged_gigs AS
SELECT
    g.id,
    g.gig_code,
    g.title,
    g.category,
    g.created_at,
    g.ai_moderation_result,
    u.username as client_username,
    u.email as client_email
FROM gig g
JOIN "user" u ON g.client_id = u.id
WHERE g.ai_moderation_result IS NOT NULL
  AND g.ai_moderation_result::jsonb->>'action' IN ('flag', 'reject')
ORDER BY g.created_at DESC;

-- Add comment to column
COMMENT ON COLUMN gig.ai_moderation_result IS 'JSON result from AI halal compliance check using Groq API';
"""

# Migration SQL for SQLite (simplified - no JSONB, no comments)
SQLITE_MIGRATION = """
-- Add ai_moderation_result column to gig table
ALTER TABLE gig
ADD COLUMN ai_moderation_result TEXT;
"""

def run_migration():
    """Execute the migration based on database type"""
    try:
        with engine.connect() as conn:
            print("\n📝 Running migration...")

            if is_postgres:
                # PostgreSQL migration with full features
                conn.execute(text(POSTGRES_MIGRATION))
                conn.commit()
                print("✅ PostgreSQL migration completed successfully")
                print("   - Added ai_moderation_result column")
                print("   - Created index on AI moderation action")
                print("   - Created ai_flagged_gigs view for admin dashboard")

            elif is_sqlite:
                # SQLite migration (basic)
                conn.execute(text(SQLITE_MIGRATION))
                conn.commit()
                print("✅ SQLite migration completed successfully")
                print("   - Added ai_moderation_result column")
                print("   ⚠️  Note: Views and JSON indexes not created (SQLite limitation)")

            else:
                print("❌ Unsupported database type")
                sys.exit(1)

            print("\n🎉 Migration completed successfully!")
            print("\nNext steps:")
            print("1. Set GROQ_API_KEY environment variable")
            print("2. Install groq package: pip install groq")
            print("3. Restart your Flask application")
            print("4. AI moderation will now run on all new gig submissions")

    except Exception as e:
        print(f"\n❌ Migration failed: {str(e)}")
        print("\nRollback:")
        print("If you need to rollback, run:")
        print("  ALTER TABLE gig DROP COLUMN ai_moderation_result;")
        sys.exit(1)


def verify_migration():
    """Verify that the migration was applied correctly"""
    try:
        with engine.connect() as conn:
            # Check if column exists
            result = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'gig'
                AND column_name = 'ai_moderation_result'
            """))

            if result.fetchone():
                print("\n✅ Verification: ai_moderation_result column exists")
                return True
            else:
                print("\n❌ Verification failed: Column not found")
                return False

    except Exception as e:
        # SQLite doesn't support information_schema, so we'll skip verification
        if is_sqlite:
            print("\n⚠️  Skipping verification (SQLite doesn't support information_schema)")
            return True
        else:
            print(f"\n❌ Verification error: {str(e)}")
            return False


if __name__ == '__main__':
    print("\n⚠️  WARNING: This migration will modify your database schema")
    print("Make sure you have a backup before proceeding!\n")

    response = input("Continue with migration? (yes/no): ")

    if response.lower() in ['yes', 'y']:
        run_migration()

        if is_postgres:
            verify_migration()
    else:
        print("\n❌ Migration cancelled by user")
        sys.exit(0)
