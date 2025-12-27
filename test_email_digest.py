#!/usr/bin/env python3
"""
Test script for email digest functionality
Run this to manually trigger the email digest and test the implementation
"""

import os
import sys

# Add the parent directory to the path so we can import app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User, Gig, NotificationPreference, EmailDigestLog
from email_service import email_service
from scheduled_jobs import send_new_gigs_digest

def test_email_digest():
    """
    Test the email digest functionality
    """
    print("=" * 80)
    print("Testing Email Digest Functionality")
    print("=" * 80)

    # Run the digest function
    print("\nTriggering send_new_gigs_digest...")
    try:
        send_new_gigs_digest(app, db, User, Gig, NotificationPreference, EmailDigestLog, email_service)
        print("\n✓ Digest function completed successfully!")
    except Exception as e:
        print(f"\n✗ Error running digest function: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

    # Check the email_digest_log table
    print("\n" + "-" * 80)
    print("Email Digest Logs:")
    print("-" * 80)

    with app.app_context():
        logs = db.session.query(EmailDigestLog).order_by(
            EmailDigestLog.sent_at.desc()
        ).limit(5).all()

        if logs:
            for log in logs:
                status = "✓ Success" if log.success else "✗ Failed"
                print(f"\nID: {log.id}")
                print(f"Type: {log.digest_type}")
                print(f"Sent At: {log.sent_at}")
                print(f"Recipients: {log.recipient_count}")
                print(f"Gigs: {log.gig_count}")
                print(f"Status: {status}")
                if log.error_message:
                    print(f"Error: {log.error_message}")
        else:
            print("No digest logs found yet")

    print("\n" + "=" * 80)
    print("Test completed!")
    print("=" * 80)
    return True

if __name__ == '__main__':
    test_email_digest()
