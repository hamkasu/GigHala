# Stripe Instant Payouts for Malaysia - Implementation Guide

## Overview

This document describes the implementation of Stripe Instant Payouts for GigHala, enabling freelancers in Malaysia to receive their earnings in approximately 30 minutes instead of waiting 3-5 business days.

## Features

- ⚡ **Instant Payouts**: Funds arrive in ~30 minutes (vs 3-5 days for standard bank transfer)
- 🇲🇾 **Malaysia Support**: Specifically designed for Malaysian bank accounts and MYR currency
- 🔗 **Stripe Connect Express**: Simplified onboarding flow for freelancers
- 💳 **Automatic Processing**: Payouts processed automatically via Stripe
- 📊 **Full Tracking**: Complete audit trail with webhook event handling

## Architecture

### 1. Database Schema

New fields added to support Stripe Connect:

**User Table**:
- `stripe_account_id` - Unique Stripe Connect account ID
- `stripe_account_status` - Account status (pending, active, restricted, rejected)
- `stripe_onboarding_completed` - Boolean flag
- `instant_payout_enabled` - Boolean flag indicating if instant payouts are available
- `stripe_account_created_at` - Timestamp

**Payout Table**:
- `is_instant` - Boolean flag for instant payouts
- `stripe_payout_id` - Stripe payout object ID
- `estimated_arrival` - Timestamp for estimated arrival

### 2. API Endpoints

#### Stripe Connect Account Management

**POST `/api/stripe/connect/account`**
- Creates a Stripe Connect Express account for the user
- Country: Malaysia (MY)
- Type: Express account with transfers capability
- Returns: Account ID and status

**POST `/api/stripe/connect/account-link`**
- Creates an onboarding link for Stripe Connect
- Redirects to Stripe's hosted onboarding flow
- Return URL: `/settings/payouts?success=true`
- Refresh URL: `/settings/payouts?refresh=true`

**GET `/api/stripe/connect/account-status`**
- Retrieves current account status
- Checks if instant payouts are enabled
- Returns requirements if onboarding incomplete

#### Instant Payout Processing

**POST `/api/stripe/connect/instant-payout`**
- Creates an instant payout via Stripe
- Required: `amount` (MYR)
- Validates: Stripe account setup, sufficient balance
- Fee Structure:
  - Stripe instant fee: RM 2.00 fixed + 2%
  - Platform fee: 2%
  - Total deducted from user's requested amount

#### Webhook Handling

**POST `/api/stripe/webhook`**
- Handles `payout.paid` event - Marks payout as completed
- Handles `payout.failed` event - Returns funds to wallet, notifies user
- Updates payout status and wallet balances
- Sends email notifications

### 3. User Flow

#### First-Time Setup
1. User navigates to Billing page and clicks "Request Payout"
2. System checks if user has Stripe Connect account
3. If not, shows "Enable Instant Payouts" button
4. User clicks button → redirected to Stripe onboarding
5. User completes bank account verification on Stripe
6. Redirected back to GigHala with instant payouts enabled

#### Requesting Instant Payout
1. User clicks "Request Payout" button
2. Modal shows "⚡ Instant Payout Available" badge
3. User selects "⚡ Instant Payout (~30 minutes)" method
4. Enters amount
5. Fees are calculated and displayed:
   - Gross amount
   - Stripe instant fee (RM 2.00 + 2%)
   - Platform fee (2%)
   - Net amount to receive
6. Submits request
7. Payout created via Stripe API
8. Email confirmation sent
9. Funds arrive in ~30 minutes
10. Webhook updates status to "completed"
11. Final confirmation email sent

### 4. Fee Structure

**Standard Payout (3-5 days)**:
- Platform fee: 2%
- No Stripe fees

**Instant Payout (~30 minutes)**:
- Stripe instant fee: RM 2.00 fixed + 2% of amount
- Platform fee: 2%
- Example for RM 100:
  - Gross: RM 100.00
  - Stripe fee: RM 2.00 + RM 2.00 = RM 4.00
  - Platform fee: RM 2.00
  - Net received: RM 94.00

## Configuration

### Environment Variables Required

```bash
# Stripe API Keys (Test Mode)
STRIPE_TEST_SECRET_KEY=sk_test_...
STRIPE_TEST_PUBLISHABLE_KEY=pk_test_...
STRIPE_TEST_WEBHOOK_SECRET=whsec_...

# Stripe API Keys (Live Mode)
STRIPE_LIVE_SECRET_KEY=sk_live_...
STRIPE_LIVE_PUBLISHABLE_KEY=pk_live_...
STRIPE_LIVE_WEBHOOK_SECRET=whsec_...

# Stripe Mode
STRIPE_MODE=test  # or 'live' for production
```

### Stripe Dashboard Setup

1. **Enable Stripe Connect**:
   - Go to Stripe Dashboard → Connect → Settings
   - Enable "Express" account type
   - Set brand name: "GigHala"
   - Upload brand logo

2. **Configure Instant Payouts**:
   - Navigate to Connect → Settings → Payouts
   - Enable "Instant payouts"
   - Select supported countries: Malaysia
   - Set default currency: MYR

3. **Set Up Webhooks**:
   - Go to Developers → Webhooks
   - Add endpoint: `https://your-domain.com/api/stripe/webhook`
   - Select events:
     - `checkout.session.completed`
     - `payment_intent.payment_failed`
     - `charge.refunded`
     - `payout.paid`
     - `payout.failed`
   - Copy webhook signing secret to `STRIPE_WEBHOOK_SECRET`

4. **Malaysia-Specific Settings**:
   - Verify Malaysia is enabled in Countries list
   - Ensure MYR is supported currency
   - Test with Malaysian test bank accounts

### Database Migration

Run the migration to add required fields:

```bash
python3 migrations/run_stripe_connect_migration.py
```

This will:
- Add Stripe Connect fields to User table
- Add instant payout fields to Payout table
- Create indexes for performance

## Testing

### Test Mode Setup

1. Use Stripe test mode keys
2. Test bank account numbers (Stripe provides test accounts for MY)
3. Webhook testing with Stripe CLI:

```bash
stripe listen --forward-to localhost:5000/api/stripe/webhook
stripe trigger payout.paid
stripe trigger payout.failed
```

### Test Scenarios

1. **New User Onboarding**:
   - Create account without Stripe Connect
   - Click "Set Up Instant Payouts"
   - Complete onboarding
   - Verify instant payout option appears

2. **Instant Payout Request**:
   - Request instant payout
   - Verify fees calculated correctly
   - Check payout created in Stripe dashboard
   - Trigger `payout.paid` webhook
   - Verify status updated to "completed"

3. **Failed Payout**:
   - Trigger `payout.failed` webhook
   - Verify funds returned to wallet
   - Check failure notification sent

4. **Incomplete Onboarding**:
   - Start onboarding but don't complete
   - Verify "Complete Setup" message shown
   - Instant payout option disabled

## Security Considerations

1. **Webhook Signature Verification**:
   - All webhooks MUST verify signatures
   - Implemented in `app.py:10069`
   - Returns 401 if signature invalid

2. **Balance Validation**:
   - Always check wallet balance before payout
   - Prevent negative balances
   - Hold balance during processing

3. **Stripe Account Verification**:
   - Verify account belongs to user
   - Check onboarding completion
   - Validate instant payout capability

4. **Rate Limiting**:
   - Consider implementing rate limits for payout requests
   - Prevent abuse of instant payout feature

## Monitoring & Logging

All financial operations are logged via `security_logger`:

- Stripe Connect account creation
- Instant payout requests
- Payout completions
- Payout failures
- Webhook events

Monitor these logs for:
- Unusual payout patterns
- Failed payouts (investigate causes)
- Webhook processing errors
- Account setup issues

## Troubleshooting

### Common Issues

**1. "Instant payouts not enabled"**
- Verify Stripe Connect onboarding completed
- Check if Malaysian bank account added
- Ensure account status is "active"

**2. "Stripe payout failed"**
- Check Stripe dashboard for failure reason
- Common causes:
  - Insufficient Stripe balance
  - Bank account issues
  - Account restrictions
- Funds automatically returned to wallet

**3. "Webhook not received"**
- Verify webhook URL is accessible
- Check webhook signing secret is correct
- Review Stripe webhook logs in dashboard
- Ensure HTTPS is enabled (required for production)

**4. "Onboarding link expired"**
- Account links expire after 24 hours
- Generate new link via "Set Up Instant Payouts" button

## Future Enhancements

Potential improvements:

1. **Auto-Payout on Completion**:
   - Automatically trigger instant payout when gig completed
   - User preference setting

2. **Payout Scheduling**:
   - Schedule weekly/monthly instant payouts
   - Minimum threshold settings

3. **Multi-Currency Support**:
   - Expand beyond MYR
   - Support for cross-border payouts

4. **Analytics Dashboard**:
   - Instant payout usage metrics
   - Fee analysis
   - Payout velocity tracking

## Support

For issues or questions:
- Email: support@gighala.com
- Stripe Support: https://support.stripe.com
- Documentation: https://stripe.com/docs/connect/instant-payouts

## References

- [Stripe Connect Documentation](https://stripe.com/docs/connect)
- [Stripe Instant Payouts](https://stripe.com/docs/payouts#instant-payouts)
- [Stripe Connect Express](https://stripe.com/docs/connect/express-accounts)
- [Malaysia Payment Methods](https://stripe.com/docs/payments/payment-methods/overview#malaysia)
