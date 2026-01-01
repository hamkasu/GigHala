#!/usr/bin/env python3
"""
Brevo Email Service Diagnostic Tool

This script helps diagnose common Brevo email delivery issues.
Run this to check your Brevo configuration and identify problems.

Usage:
    python diagnose_brevo.py
"""
import os
import sys
from dotenv import load_dotenv
import brevo_python
from brevo_python.rest import ApiException

# Load environment variables
load_dotenv()

def check_environment():
    """Check if required environment variables are set"""
    print("=" * 60)
    print("STEP 1: Checking Environment Variables")
    print("=" * 60)

    api_key = os.environ.get('BREVO_API_KEY')
    from_email = os.environ.get('BREVO_FROM_EMAIL')
    from_name = os.environ.get('BREVO_FROM_NAME', 'GigHala')

    issues = []

    if not api_key:
        print("❌ BREVO_API_KEY is not set")
        issues.append("Missing BREVO_API_KEY")
    else:
        # Mask the API key for security
        masked_key = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
        print(f"✓ BREVO_API_KEY is set: {masked_key}")

    if not from_email:
        print("❌ BREVO_FROM_EMAIL is not set")
        issues.append("Missing BREVO_FROM_EMAIL")
    else:
        print(f"✓ BREVO_FROM_EMAIL is set: {from_email}")

    print(f"✓ BREVO_FROM_NAME is set: {from_name}")
    print()

    return api_key, from_email, from_name, issues

def check_api_connection(api_key):
    """Check if API key is valid and account is accessible"""
    print("=" * 60)
    print("STEP 2: Testing API Connection")
    print("=" * 60)

    if not api_key:
        print("❌ Cannot test API - API key not set")
        print()
        return False, ["API key not configured"]

    issues = []

    try:
        # Configure API client
        configuration = brevo_python.Configuration()
        configuration.api_key['api-key'] = api_key
        api_client = brevo_python.ApiClient(configuration)

        # Try to get account information
        account_api = brevo_python.AccountApi(api_client)
        account_info = account_api.get_account()

        print(f"✓ API connection successful")
        print(f"✓ Account email: {account_info.email}")
        print(f"✓ Company name: {account_info.company_name}")

        # Check account plan
        if hasattr(account_info, 'plan'):
            print(f"✓ Plan: {account_info.plan[0].type if account_info.plan else 'Unknown'}")

        print()
        return True, issues

    except ApiException as e:
        print(f"❌ API connection failed: {e.status}")
        if e.status == 401:
            print("   This usually means your API key is invalid or expired")
            issues.append("Invalid or expired API key (401 Unauthorized)")
        else:
            print(f"   Error details: {e.reason}")
            issues.append(f"API error: {e.status} {e.reason}")
        print()
        return False, issues
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        issues.append(f"Unexpected error: {str(e)}")
        print()
        return False, issues

def check_senders(api_key, from_email):
    """Check if sender email is verified"""
    print("=" * 60)
    print("STEP 3: Checking Sender Verification")
    print("=" * 60)

    if not api_key or not from_email:
        print("❌ Cannot check senders - missing configuration")
        print()
        return ["Missing API key or from_email"]

    issues = []

    try:
        # Configure API client
        configuration = brevo_python.Configuration()
        configuration.api_key['api-key'] = api_key
        api_client = brevo_python.ApiClient(configuration)

        # Get senders list
        senders_api = brevo_python.SendersApi(api_client)
        senders_list = senders_api.get_senders()

        if not senders_list or not senders_list.senders:
            print("❌ No senders found in your Brevo account")
            print("   You need to add and verify a sender email address")
            issues.append("No senders configured")
            print()
            return issues

        # Check if from_email is in the list of verified senders
        sender_found = False
        sender_active = False

        print(f"Found {len(senders_list.senders)} sender(s) in your account:")
        print()

        for sender in senders_list.senders:
            is_current = sender.email.lower() == from_email.lower()
            status_symbol = "✓" if sender.active else "❌"
            current_marker = " ← CURRENT" if is_current else ""

            print(f"{status_symbol} {sender.email} (Name: {sender.name})")
            print(f"   Active: {sender.active}{current_marker}")

            if hasattr(sender, 'ips'):
                print(f"   IPs: {sender.ips if sender.ips else 'Default'}")

            if is_current:
                sender_found = True
                sender_active = sender.active

            print()

        if not sender_found:
            print(f"❌ Your configured sender ({from_email}) is NOT in the verified senders list")
            print(f"   You need to add and verify this email address in Brevo")
            issues.append(f"Sender email {from_email} not found in verified senders")
        elif not sender_active:
            print(f"❌ Your sender ({from_email}) is found but NOT ACTIVE")
            print(f"   You need to verify this email address to activate it")
            issues.append(f"Sender email {from_email} is not active/verified")
        else:
            print(f"✓ Your sender ({from_email}) is properly configured and active")

        print()
        return issues

    except ApiException as e:
        print(f"❌ Failed to check senders: {e.status} {e.reason}")
        issues.append(f"Cannot check senders: {e.status} {e.reason}")
        print()
        return issues
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        issues.append(f"Unexpected error checking senders: {str(e)}")
        print()
        return issues

def send_test_email(api_key, from_email, from_name):
    """Send a test email"""
    print("=" * 60)
    print("STEP 4: Send Test Email (Optional)")
    print("=" * 60)

    if not api_key or not from_email:
        print("❌ Cannot send test email - missing configuration")
        print()
        return

    # Ask user if they want to send a test email
    response = input("Do you want to send a test email? (yes/no): ").strip().lower()

    if response not in ['yes', 'y']:
        print("Skipping test email")
        print()
        return

    test_email = input("Enter email address to send test to: ").strip()

    if not test_email or '@' not in test_email:
        print("Invalid email address")
        print()
        return

    try:
        # Configure API client
        configuration = brevo_python.Configuration()
        configuration.api_key['api-key'] = api_key
        api_client = brevo_python.ApiClient(configuration)
        api_instance = brevo_python.TransactionalEmailsApi(api_client)

        # Create test email
        send_smtp_email = brevo_python.SendSmtpEmail(
            to=[{"email": test_email}],
            sender={"email": from_email, "name": from_name},
            subject="Brevo Test Email - GigHala",
            html_content="""
            <html>
                <body>
                    <h1>Test Email from GigHala</h1>
                    <p>This is a test email to verify your Brevo configuration.</p>
                    <p>If you received this email, your Brevo setup is working correctly!</p>
                    <hr>
                    <p><small>Sent via Brevo API</small></p>
                </body>
            </html>
            """,
            text_content="Test Email from GigHala - If you received this, your Brevo setup is working!"
        )

        # Send the email
        api_response = api_instance.send_transac_email(send_smtp_email)

        if api_response and hasattr(api_response, 'message_id'):
            print(f"✓ Test email sent successfully!")
            print(f"  Message ID: {api_response.message_id}")
            print(f"  Check {test_email} for the test email")
            print()
            print("IMPORTANT: If you don't receive this email:")
            print("  1. Check your spam/junk folder")
            print("  2. Verify the sender email in Brevo dashboard")
            print("  3. Check Brevo's transactional email logs")
            print()
        else:
            print("❌ Email was accepted but no message ID returned")
            print()

    except ApiException as e:
        print(f"❌ Failed to send test email: {e.status}")
        print(f"   Error: {e.reason}")
        if e.status == 400:
            print("   This usually means there's a problem with the sender or recipient")
        print()
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        print()

def print_summary(all_issues):
    """Print summary and recommendations"""
    print("=" * 60)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 60)

    if not all_issues:
        print("✓ No issues detected!")
        print()
        print("Your Brevo configuration appears to be correct.")
        print("If emails are still not being delivered:")
        print("  1. Check recipient spam/junk folders")
        print("  2. Review Brevo transactional logs: https://app.brevo.com/email/logs")
        print("  3. Verify domain authentication (SPF/DKIM)")
    else:
        print(f"Found {len(all_issues)} issue(s):")
        print()
        for i, issue in enumerate(all_issues, 1):
            print(f"{i}. {issue}")
        print()
        print("=" * 60)
        print("RECOMMENDED ACTIONS")
        print("=" * 60)
        print()
        print("To fix email delivery issues, follow these steps:")
        print()
        print("1. LOG IN TO BREVO DASHBOARD")
        print("   https://app.brevo.com/")
        print()
        print("2. VERIFY YOUR SENDER EMAIL")
        print("   - Go to: Senders & IP → Senders")
        print("   - Click 'Add a new sender'")
        print(f"   - Add: {os.environ.get('BREVO_FROM_EMAIL', 'your-email@domain.com')}")
        print("   - Check your email for a 6-digit verification code")
        print("   - Enter the code to verify the sender")
        print()
        print("3. AUTHENTICATE YOUR DOMAIN (Recommended)")
        print("   - Go to: Senders & IP → Domains")
        print("   - Add your domain and follow DNS setup instructions")
        print("   - Add SPF and DKIM records to your domain's DNS")
        print()
        print("4. CHECK ACCOUNT STATUS")
        print("   - Make sure your account is not suspended")
        print("   - Check you haven't exceeded your daily sending limit")
        print("   - Free accounts: 300 emails/day")
        print()
        print("5. REVIEW TRANSACTIONAL LOGS")
        print("   - Go to: Transactional → Logs")
        print("   - Check the status of recent emails")
        print("   - Look for bounce/block reasons")
        print()

    print("=" * 60)
    print("For more help, visit: https://help.brevo.com/")
    print("=" * 60)

def main():
    """Main diagnostic function"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 58 + "║")
    print("║" + "  Brevo Email Service Diagnostic Tool".center(58) + "║")
    print("║" + "  GigHala".center(58) + "║")
    print("║" + " " * 58 + "║")
    print("╚" + "=" * 58 + "╝")
    print()

    all_issues = []

    # Step 1: Check environment variables
    api_key, from_email, from_name, env_issues = check_environment()
    all_issues.extend(env_issues)

    # Step 2: Check API connection
    if api_key:
        api_ok, api_issues = check_api_connection(api_key)
        all_issues.extend(api_issues)

        # Step 3: Check senders only if API is working
        if api_ok:
            sender_issues = check_senders(api_key, from_email)
            all_issues.extend(sender_issues)

            # Step 4: Optionally send test email
            send_test_email(api_key, from_email, from_name)

    # Print summary and recommendations
    print_summary(all_issues)

    # Exit with appropriate code
    sys.exit(1 if all_issues else 0)

if __name__ == "__main__":
    main()
