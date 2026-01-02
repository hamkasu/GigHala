#!/usr/bin/env python3
"""
Database Migration Script to Normalize User Email Addresses

This ensures consistency between OAuth users (who may have non-normalized emails)
and regular users (who have normalized emails from registration).

This migration is critical to fix the login failure issue where OAuth users
cannot log in with email/password because their emails are stored differently
than how the login function normalizes them.
"""

import sys
from pathlib import Path

# Add parent directory to path to import app
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app, db, User
from email_validator import validate_email, EmailNotValidError

def normalize_all_emails():
    """Normalize all user email addresses in the database"""
    users = User.query.all()
    updated_count = 0
    error_count = 0

    print(f"\n📧 Found {len(users)} users to check...")
    print("-" * 60)

    for user in users:
        original_email = user.email

        try:
            # Normalize the email
            email_info = validate_email(original_email, check_deliverability=False)
            normalized_email = email_info.normalized

            if original_email != normalized_email:
                print(f"\n👤 User ID {user.id} ({user.username}):")
                print(f"   Original:   {repr(original_email)}")
                print(f"   Normalized: {repr(normalized_email)}")

                # Check if normalized email already exists for a different user
                existing_user = User.query.filter(
                    User.email == normalized_email,
                    User.id != user.id
                ).first()

                if existing_user:
                    print(f"   ⚠️  CONFLICT: Normalized email already exists for user {existing_user.id} ({existing_user.username})")
                    print(f"   Skipping update to avoid duplicate email constraint violation")
                    error_count += 1
                else:
                    # Update the email
                    user.email = normalized_email
                    updated_count += 1
                    print(f"   ✅ Updated")

        except EmailNotValidError as e:
            print(f"\n⚠️  User ID {user.id} has invalid email '{original_email}': {e}")
            error_count += 1

    if updated_count > 0:
        try:
            db.session.commit()
            print("\n" + "-" * 60)
            print(f"✅ Successfully updated {updated_count} user email(s)")
            if error_count > 0:
                print(f"⚠️  {error_count} user(s) skipped due to errors or conflicts")
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Error committing changes: {e}")
            return False
    else:
        print("\n" + "-" * 60)
        print("ℹ️  No email updates needed - all emails are already normalized")
        if error_count > 0:
            print(f"⚠️  {error_count} user(s) have errors")

    return True


def main():
    """Main migration entry point"""
    print("=" * 60)
    print("GigHala Email Normalization Migration")
    print("=" * 60)

    try:
        success = normalize_all_emails()

        if success:
            print("\n✅ Migration completed successfully!")
            print("\n📝 Summary:")
            print("   This migration normalizes all user email addresses to ensure")
            print("   consistency between OAuth and regular authentication.")
            print("\n🚀 Your users can now log in with email/password successfully!")
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
