"""
Script to send AI Matching System announcement email to all users
Run this once to announce the new feature to existing users
"""

import os
import sys
from datetime import datetime
from flask import render_template

# Add the parent directory to the path so we can import app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User, NotificationPreference
from email_service import EmailService


def send_ai_announcement_emails(test_mode=True, test_email=None, language='ms'):
    """
    Send AI matching announcement to all users

    Args:
        test_mode: If True, only send to test_email
        test_email: Email address for testing
        language: 'ms' (Malay) or 'en' (English) - currently only 'ms' template available
    """
    with app.app_context():
        print(f"\n{'='*80}")
        print(f"AI Matching System - Announcement Email Sender")
        print(f"{'='*80}\n")

        # Initialize email service
        email_service = EmailService()

        # Get base URL
        base_url = os.getenv('BASE_URL', 'https://gighala.my')

        if test_mode:
            if not test_email:
                print("❌ Error: test_email is required in test mode")
                return

            print(f"🧪 TEST MODE - Sending to: {test_email}\n")

            # Create test user data
            users_to_email = [{
                'email': test_email,
                'full_name': 'Test User',
                'username': 'testuser',
                'language': language
            }]
        else:
            # Get all users who want email notifications
            print("📊 Fetching users from database...\n")

            users_query = db.session.query(User).outerjoin(
                NotificationPreference,
                User.id == NotificationPreference.user_id
            ).filter(
                User.email.isnot(None)
            )

            users_to_email = []
            for user in users_query.all():
                pref = db.session.query(NotificationPreference).filter_by(
                    user_id=user.id
                ).first()

                # If no preference exists, or if email_new_gig is True
                if not pref or pref.email_new_gig:
                    users_to_email.append({
                        'email': user.email,
                        'full_name': user.full_name,
                        'username': user.username,
                        'language': user.language or 'ms'
                    })

            print(f"✅ Found {len(users_to_email)} users to email\n")

            # Confirm before sending
            response = input(f"⚠️  Are you sure you want to send to {len(users_to_email)} users? (yes/no): ")
            if response.lower() != 'yes':
                print("❌ Cancelled by user")
                return

        # Send emails
        successful_sends = 0
        failed_sends = 0
        failed_recipients = []

        total_emails = len(users_to_email)

        for idx, user_data in enumerate(users_to_email, 1):
            try:
                user_name = user_data['full_name'] or user_data['username'] or 'Pengguna'
                user_email = user_data['email']
                user_lang = user_data.get('language', 'ms')

                print(f"📧 Sending email {idx}/{total_emails} to {user_email}...")

                # Render email template
                with app.test_request_context():
                    # Use Malay template (can add English version later)
                    html_content = render_template(
                        'email_ai_matching_announcement_malay.html',
                        user_name=user_name,
                        base_url=base_url
                    )

                # Subject based on language
                if user_lang == 'ms':
                    subject = "🤖 Sistem Padanan AI Baharu - Dapatkan Gig Yang Sesuai!"
                else:
                    subject = "🤖 New AI Matching System - Get Relevant Gigs!"

                # Send email
                success, message, status_code, details = email_service.send_single_email(
                    to_email=user_email,
                    to_name=user_name,
                    subject=subject,
                    html_content=html_content
                )

                if success:
                    successful_sends += 1
                    print(f"   ✓ Sent successfully\n")
                else:
                    failed_sends += 1
                    failed_recipients.append(user_email)
                    print(f"   ✗ Failed: {message}\n")

                # Small delay to avoid rate limiting (optional)
                if not test_mode and idx % 10 == 0:
                    import time
                    time.sleep(1)

            except Exception as e:
                failed_sends += 1
                failed_recipients.append(user_data['email'])
                print(f"   ✗ Error: {str(e)}\n")

        # Summary
        print(f"\n{'='*80}")
        print(f"SUMMARY")
        print(f"{'='*80}")
        print(f"✅ Successful: {successful_sends}")
        print(f"❌ Failed: {failed_sends}")
        print(f"📊 Total: {total_emails}")

        if failed_recipients:
            print(f"\nFailed recipients:")
            for email in failed_recipients[:10]:
                print(f"  - {email}")
            if len(failed_recipients) > 10:
                print(f"  ... and {len(failed_recipients) - 10} more")

        print(f"\n{'='*80}\n")


def send_test_email():
    """Send a test email to verify template"""
    test_email = input("Enter test email address: ").strip()
    if not test_email:
        print("❌ No email provided")
        return

    language = input("Language (ms/en) [default: ms]: ").strip() or 'ms'

    send_ai_announcement_emails(
        test_mode=True,
        test_email=test_email,
        language=language
    )


def send_to_all_users():
    """Send to all users - production mode"""
    print("\n⚠️  WARNING: This will send emails to ALL users!")
    print("Make sure you have:")
    print("  1. Tested the email template")
    print("  2. Configured BREVO_API_KEY in .env")
    print("  3. Set the correct BASE_URL in .env")
    print()

    confirm = input("Type 'SEND TO ALL' to confirm: ").strip()
    if confirm != 'SEND TO ALL':
        print("❌ Cancelled")
        return

    send_ai_announcement_emails(test_mode=False)


if __name__ == '__main__':
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║          GigHala AI Matching - Announcement Sender           ║
    ╚══════════════════════════════════════════════════════════════╝
    """)

    if len(sys.argv) > 1:
        if sys.argv[1] == 'test':
            # Command line test mode
            test_email = sys.argv[2] if len(sys.argv) > 2 else None
            if not test_email:
                print("Usage: python send_ai_announcement.py test <email@example.com>")
                sys.exit(1)

            language = sys.argv[3] if len(sys.argv) > 3 else 'ms'
            send_ai_announcement_emails(
                test_mode=True,
                test_email=test_email,
                language=language
            )

        elif sys.argv[1] == 'all':
            # Command line production mode
            send_to_all_users()

        else:
            print("Usage:")
            print("  python send_ai_announcement.py test <email@example.com> [language]")
            print("  python send_ai_announcement.py all")

    else:
        # Interactive mode
        while True:
            print("\nOptions:")
            print("1. Send test email")
            print("2. Send to all users (PRODUCTION)")
            print("3. Exit")
            print()

            choice = input("Select option (1-3): ").strip()

            if choice == '1':
                send_test_email()
            elif choice == '2':
                send_to_all_users()
            elif choice == '3':
                print("Goodbye!")
                break
            else:
                print("❌ Invalid option")

            if choice in ['1', '2']:
                input("\nPress Enter to continue...")
