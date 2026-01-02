# Stripe Test/Live Mode Setup Guide

GigHala now supports switching between Stripe test mode (sandbox) and live mode (production) through the admin panel.

## Overview

- **Test Mode**: Uses sandbox API keys for testing without processing real money
- **Live Mode**: Uses production API keys for real transactions with actual payments

## Environment Variables Setup

### 1. Add Stripe Keys to Your Environment

You need to configure separate API keys for test and live modes:

#### Test Mode Keys (Sandbox)
```bash
STRIPE_TEST_SECRET_KEY=sk_test_your_test_secret_key_here
STRIPE_TEST_PUBLISHABLE_KEY=pk_test_your_test_publishable_key_here
STRIPE_TEST_WEBHOOK_SECRET=whsec_test_your_webhook_secret_here
```

#### Live Mode Keys (Production)
```bash
STRIPE_LIVE_SECRET_KEY=sk_live_your_live_secret_key_here
STRIPE_LIVE_PUBLISHABLE_KEY=pk_live_your_live_publishable_key_here
STRIPE_LIVE_WEBHOOK_SECRET=whsec_live_your_webhook_secret_here
```

#### Legacy Keys (Optional - for backward compatibility)
```bash
STRIPE_SECRET_KEY=your_default_key_here
STRIPE_PUBLISHABLE_KEY=your_default_publishable_key_here
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret_here
```

**Note**: If test/live specific keys are not set, the system will fall back to the legacy keys.

### 2. Get Your Stripe API Keys

1. Log in to your [Stripe Dashboard](https://dashboard.stripe.com/)
2. For **Test Mode** keys:
   - Toggle to "Test mode" in the dashboard
   - Go to Developers → API keys
   - Copy your test keys (they start with `sk_test_` and `pk_test_`)
3. For **Live Mode** keys:
   - Toggle to "Live mode" in the dashboard
   - Go to Developers → API keys
   - Copy your live keys (they start with `sk_live_` and `pk_live_`)

## Admin Panel Configuration

### Switching Between Modes

1. Log in as an admin
2. Go to the **Admin Dashboard**
3. Click on the **Settings** tab
4. Scroll down to the **Stripe Transaction Mode** section
5. You'll see two cards:
   - **Test Mode** 🧪 - For development and testing
   - **Live Mode** 🔴 - For real production transactions

### Status Indicators

Each mode card shows:
- ✓ **Keys Configured**: The API keys for this mode are properly set
- ✗ **Not Configured**: The API keys are missing or invalid

### Switching Modes

1. Click on the mode card you want to switch to
2. Click the **"Save Stripe Mode"** button
3. For **Live Mode**, you'll see a confirmation warning:
   ```
   ⚠️ WARNING: You are about to switch to LIVE mode.

   This will process REAL transactions with REAL money.

   Are you sure you want to continue?
   ```
4. Confirm to apply the change

## Safety Features

### Automatic Protection

- **Default Mode**: The system defaults to Test Mode for safety
- **Key Validation**: The system checks if the required keys are configured before allowing mode changes
- **Live Mode Confirmation**: A confirmation dialog prevents accidental switches to live mode

### Current Mode Display

The active mode is displayed in the status section:
- 🧪 **Current mode: TEST (Sandbox)** - No real money is charged
- 🔴 **Current mode: LIVE (Production)** - Real transactions are processed

## Testing Your Setup

### Test Mode Testing

1. Switch to Test Mode in the admin panel
2. Use Stripe's [test card numbers](https://stripe.com/docs/testing):
   - `4242 4242 4242 4242` - Successful payment
   - `4000 0000 0000 9995` - Declined payment
3. Use any future expiry date and any 3-digit CVC
4. No real money will be charged

### Live Mode Testing

⚠️ **Warning**: Live mode processes real payments!

1. **Before switching to live mode**, ensure:
   - Your Stripe account is fully activated
   - Your live API keys are correctly configured
   - You're ready to accept real payments
   - All testing is complete in test mode

2. Only switch to live mode when you're ready for production

## Troubleshooting

### "Keys are not configured" Error

**Problem**: The mode you're trying to switch to doesn't have API keys configured.

**Solution**:
1. Check your environment variables
2. Ensure the correct keys are set:
   - For test mode: `STRIPE_TEST_SECRET_KEY` and `STRIPE_TEST_PUBLISHABLE_KEY`
   - For live mode: `STRIPE_LIVE_SECRET_KEY` and `STRIPE_LIVE_PUBLISHABLE_KEY`
3. Restart your application after adding environment variables

### Payments Not Working

**Problem**: Payments fail or show errors.

**Solution**:
1. Check which mode you're in (Test or Live)
2. Verify you're using the correct test card numbers for test mode
3. Check Stripe Dashboard → Logs for detailed error messages
4. Ensure webhook secrets are configured if using webhooks

### Can't Switch Modes

**Problem**: The "Save Stripe Mode" button doesn't appear or doesn't work.

**Solution**:
1. Ensure you're logged in as an admin
2. Check browser console for JavaScript errors
3. Verify the API keys for the target mode are configured
4. Try refreshing the page

## Best Practices

1. **Always Test First**: Thoroughly test in test mode before going live
2. **Monitor Initially**: When first switching to live mode, closely monitor the first few transactions
3. **Backup Keys**: Securely store your API keys in a password manager
4. **Use Environment Variables**: Never hardcode API keys in your code
5. **Regular Checks**: Periodically verify your mode setting matches your intention

## API Endpoints

For developers integrating with the mode switching:

### Get Current Mode
```
GET /api/admin/settings/stripe-mode
```

Response:
```json
{
  "mode": "test",
  "test_configured": true,
  "live_configured": false,
  "current_key_set": true
}
```

### Set Mode
```
POST /api/admin/settings/stripe-mode
Content-Type: application/json

{
  "mode": "live"
}
```

Response:
```json
{
  "message": "Stripe mode set to live",
  "mode": "live"
}
```

## Security Notes

- API keys are never exposed to the frontend
- Mode switching requires admin privileges
- All Stripe operations use the currently configured mode
- The system automatically reinitializes Stripe when the mode changes

## Support

If you encounter issues:
1. Check the application logs for detailed error messages
2. Verify your Stripe Dashboard for payment status
3. Ensure your environment variables are correctly set
4. Contact Stripe support for payment-related issues
