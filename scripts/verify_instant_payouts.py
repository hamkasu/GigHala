#!/usr/bin/env python3
"""
Instant Payouts Configuration Verification Script

This script checks if all components for Stripe Instant Payouts are properly configured.
Run this before enabling instant payouts in production.

Usage:
    python3 scripts/verify_instant_payouts.py
"""

import os
import sys
from dotenv import load_dotenv
import stripe

# Colors for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_header(text):
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{text.center(60)}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")

def print_success(text):
    print(f"{GREEN}✅ {text}{RESET}")

def print_error(text):
    print(f"{RED}❌ {text}{RESET}")

def print_warning(text):
    print(f"{YELLOW}⚠️  {text}{RESET}")

def print_info(text):
    print(f"ℹ️  {text}")

def check_env_variables():
    """Check if required environment variables are set"""
    print_header("Checking Environment Variables")

    required_vars = {
        'STRIPE_MODE': False,
        'STRIPE_TEST_SECRET_KEY': False,
        'STRIPE_TEST_PUBLISHABLE_KEY': False,
        'STRIPE_TEST_WEBHOOK_SECRET': False,
    }

    optional_vars = {
        'STRIPE_LIVE_SECRET_KEY': False,
        'STRIPE_LIVE_PUBLISHABLE_KEY': False,
        'STRIPE_LIVE_WEBHOOK_SECRET': False,
    }

    all_passed = True

    # Check required variables
    for var in required_vars:
        value = os.getenv(var)
        if value and len(value) > 0:
            required_vars[var] = True
            if 'SECRET' in var or 'KEY' in var:
                masked = value[:10] + '...' + value[-4:]
                print_success(f"{var}: {masked}")
            else:
                print_success(f"{var}: {value}")
        else:
            required_vars[var] = False
            print_error(f"{var}: NOT SET")
            all_passed = False

    # Check optional variables (for live mode)
    print(f"\n{YELLOW}Live Mode Keys (optional for testing):{RESET}")
    for var in optional_vars:
        value = os.getenv(var)
        if value and len(value) > 0:
            optional_vars[var] = True
            if 'SECRET' in var or 'KEY' in var:
                masked = value[:10] + '...' + value[-4:]
                print_success(f"{var}: {masked}")
            else:
                print_success(f"{var}: {value}")
        else:
            print_warning(f"{var}: NOT SET (required for production)")

    return all_passed

def check_stripe_connection():
    """Test connection to Stripe API"""
    print_header("Testing Stripe API Connection")

    stripe_mode = os.getenv('STRIPE_MODE', 'test')

    if stripe_mode == 'test':
        stripe.api_key = os.getenv('STRIPE_TEST_SECRET_KEY')
    else:
        stripe.api_key = os.getenv('STRIPE_LIVE_SECRET_KEY')

    if not stripe.api_key:
        print_error("Stripe API key not found")
        return False

    try:
        # Try to retrieve account info
        account = stripe.Account.retrieve()
        print_success(f"Connected to Stripe account: {account.id}")
        print_info(f"  Business name: {account.business_profile.name or 'Not set'}")
        print_info(f"  Country: {account.country}")
        print_info(f"  Currency: {account.default_currency.upper()}")
        print_info(f"  Charges enabled: {account.charges_enabled}")
        print_info(f"  Payouts enabled: {account.payouts_enabled}")

        # Check if Connect is enabled
        if account.controller:
            print_success("Stripe Connect is enabled")
        else:
            print_warning("Stripe Connect may not be fully enabled")

        return True
    except stripe.error.AuthenticationError:
        print_error("Invalid Stripe API key")
        return False
    except Exception as e:
        print_error(f"Error connecting to Stripe: {str(e)}")
        return False

def check_database_schema():
    """Check if database has required Stripe fields"""
    print_header("Checking Database Schema")

    try:
        # Import app and models
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from app import User, Payout

        # Check User model
        print("Checking User model fields:")
        user_fields = ['stripe_account_id', 'stripe_account_status',
                       'stripe_onboarding_completed', 'instant_payout_enabled',
                       'stripe_account_created_at']

        user_passed = True
        for field in user_fields:
            if hasattr(User, field):
                print_success(f"  {field}")
            else:
                print_error(f"  {field}")
                user_passed = False

        # Check Payout model
        print("\nChecking Payout model fields:")
        payout_fields = ['is_instant', 'stripe_payout_id', 'estimated_arrival']

        payout_passed = True
        for field in payout_fields:
            if hasattr(Payout, field):
                print_success(f"  {field}")
            else:
                print_error(f"  {field}")
                payout_passed = False

        if user_passed and payout_passed:
            print_success("\nAll database fields are present")
            return True
        else:
            print_error("\nSome database fields are missing")
            print_info("Run: python3 migrations/run_stripe_connect_migration.py")
            return False

    except ImportError as e:
        print_error(f"Could not import app models: {str(e)}")
        return False
    except Exception as e:
        print_error(f"Error checking database schema: {str(e)}")
        return False

def check_api_endpoints():
    """Check if required API endpoints exist"""
    print_header("Checking API Endpoints")

    try:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from app import app

        required_endpoints = [
            ('POST', '/api/stripe/connect/account', 'Create Stripe Connect account'),
            ('POST', '/api/stripe/connect/account-link', 'Generate onboarding link'),
            ('GET', '/api/stripe/connect/account-status', 'Check account status'),
            ('POST', '/api/stripe/connect/instant-payout', 'Create instant payout'),
            ('POST', '/api/stripe/webhook', 'Handle Stripe webhooks'),
        ]

        all_passed = True
        for method, endpoint, description in required_endpoints:
            # Check if route exists
            found = False
            for rule in app.url_map.iter_rules():
                if rule.rule == endpoint and method in rule.methods:
                    found = True
                    break

            if found:
                print_success(f"{method:6} {endpoint:45} ({description})")
            else:
                print_error(f"{method:6} {endpoint:45} ({description})")
                all_passed = False

        return all_passed

    except Exception as e:
        print_error(f"Error checking API endpoints: {str(e)}")
        return False

def check_webhook_configuration():
    """Check webhook configuration in Stripe"""
    print_header("Checking Webhook Configuration")

    webhook_secret = os.getenv('STRIPE_TEST_WEBHOOK_SECRET') or os.getenv('STRIPE_LIVE_WEBHOOK_SECRET')

    if not webhook_secret:
        print_error("Webhook secret not configured")
        print_info("Set STRIPE_TEST_WEBHOOK_SECRET in .env")
        return False

    if webhook_secret.startswith('whsec_'):
        print_success(f"Webhook secret configured: {webhook_secret[:15]}...")
    else:
        print_warning("Webhook secret format looks unusual (should start with 'whsec_')")
        return False

    # List required webhook events
    print("\nRequired webhook events:")
    required_events = [
        'payout.paid',
        'payout.failed',
        'checkout.session.completed',
        'payment_intent.payment_failed',
        'charge.refunded'
    ]

    for event in required_events:
        print_info(f"  • {event}")

    print_warning("\nManually verify these events are configured in Stripe Dashboard:")
    print_info("https://dashboard.stripe.com/webhooks")

    return True

def run_all_checks():
    """Run all verification checks"""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{'Instant Payouts Configuration Verification'.center(60)}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")

    results = {
        'Environment Variables': False,
        'Stripe Connection': False,
        'Database Schema': False,
        'API Endpoints': False,
        'Webhook Configuration': False,
    }

    # Load environment variables
    load_dotenv()

    # Run checks
    results['Environment Variables'] = check_env_variables()
    results['Stripe Connection'] = check_stripe_connection()
    results['Database Schema'] = check_database_schema()
    results['API Endpoints'] = check_api_endpoints()
    results['Webhook Configuration'] = check_webhook_configuration()

    # Print summary
    print_header("Verification Summary")

    all_passed = True
    for check, passed in results.items():
        if passed:
            print_success(f"{check:30} PASSED")
        else:
            print_error(f"{check:30} FAILED")
            all_passed = False

    print("\n" + "="*60 + "\n")

    if all_passed:
        print_success("🎉 All checks passed! Instant Payouts are ready to use.")
        print_info("\nNext steps:")
        print_info("  1. Test with a real user account")
        print_info("  2. Complete Stripe onboarding")
        print_info("  3. Request a test instant payout")
        print_info("  4. Verify webhook handling")
        print_info("  5. When ready, switch to live mode")
        return 0
    else:
        print_error("❌ Some checks failed. Please fix the issues above.")
        print_info("\nReferences:")
        print_info("  • Setup Guide: docs/INSTANT_PAYOUTS_SETUP_GUIDE.md")
        print_info("  • Quick Start: docs/INSTANT_PAYOUTS_QUICK_START.md")
        print_info("  • Technical Docs: STRIPE_INSTANT_PAYOUTS.md")
        return 1

if __name__ == '__main__':
    exit_code = run_all_checks()
    sys.exit(exit_code)
