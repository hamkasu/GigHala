# Stripe Payment Gateway Setup Guide

Complete guide for integrating and configuring Stripe payments in GigHala.

## Table of Contents
1. [Overview](#overview)
2. [Features](#features)
3. [Prerequisites](#prerequisites)
4. [Configuration](#configuration)
5. [Database Setup](#database-setup)
6. [Webhook Configuration](#webhook-configuration)
7. [Testing](#testing)
8. [Production Deployment](#production-deployment)
9. [API Endpoints](#api-endpoints)
10. [Troubleshooting](#troubleshooting)

---

## Overview

GigHala uses Stripe as a payment gateway for escrow funding with the following capabilities:
- Secure card payments (Visa, Mastercard, AMEX)
- Saved payment methods for repeat customers
- Full and partial refunds
- Automated webhook processing
- Comprehensive audit logging

**Currency:** Malaysian Ringgit (MYR)
**Processing Fees:** 2.9% + RM 1.00 per transaction

---

## Features

### ✅ Implemented Features

1. **Escrow Funding**
   - One-time card payments via Stripe Checkout
   - Automatic escrow funding on successful payment
   - Platform fee and processing fee breakdown

2. **Refunds**
   - Full refunds to original payment method
   - Partial refunds with tracking
   - Automatic Stripe refund processing
   - Refund notifications

3. **Saved Payment Methods**
   - Save cards for future payments
   - List saved payment methods
   - Delete payment methods
   - Secure customer management

4. **Webhook Processing**
   - Automated payment confirmation
   - Failed payment handling
   - Refund event tracking
   - Complete audit log

5. **Error Handling**
   - Detailed error logging
   - Stripe error handling
   - Webhook retry support
   - Database transaction safety

---

## Prerequisites

1. **Stripe Account**
   - Sign up at https://stripe.com
   - Complete account verification
   - Activate MYR currency support

2. **API Keys**
   - Publishable key (starts with `pk_`)
   - Secret key (starts with `sk_`)
   - Webhook signing secret (starts with `whsec_`)

3. **System Requirements**
   - Python 3.8+
   - PostgreSQL database
   - HTTPS domain (required for production)

---

## Configuration

### 1. Environment Variables

Add these to your `.env` file:

```bash
# Stripe Configuration
STRIPE_SECRET_KEY=sk_test_your_secret_key_here
STRIPE_PUBLISHABLE_KEY=pk_test_your_publishable_key_here
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret_here

# Application URL (for webhook callbacks)
BASE_URL=https://yourdomain.com
```

### 2. Test vs Production Keys

**Test Mode (Development):**
```bash
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_test_...
```

**Live Mode (Production):**
```bash
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_WEBHOOK_SECRET=whsec_live_...
```

---

## Database Setup

### Run Migrations

Execute the following SQL migrations in order:

```bash
# 1. Add payment gateway tracking to escrow
psql -d gighala < migrations/add_payment_gateway_to_escrow.sql

# 2. Add partial refund support
psql -d gighala < migrations/add_partial_refund_support.sql

# 3. Add saved payment methods support
psql -d gighala < migrations/add_stripe_customer_id.sql

# 4. Add webhook logging
psql -d gighala < migrations/add_stripe_webhook_log.sql
```

### Verify Tables

Check that these fields exist:

```sql
-- Escrow table
SELECT payment_gateway, refunded_amount FROM escrow LIMIT 1;

-- User table
SELECT stripe_customer_id FROM "user" LIMIT 1;

-- Webhook log table
SELECT * FROM stripe_webhook_log LIMIT 1;
```

---

## Webhook Configuration

### 1. Create Webhook Endpoint

In your Stripe Dashboard:

1. Go to **Developers → Webhooks**
2. Click **Add endpoint**
3. Enter your webhook URL:
   ```
   https://yourdomain.com/api/stripe/webhook
   ```
4. Select events to listen for:
   - `checkout.session.completed`
   - `payment_intent.payment_failed`
   - `charge.refunded`

5. Copy the **Signing secret** (starts with `whsec_`)
6. Add to your `.env` as `STRIPE_WEBHOOK_SECRET`

### 2. Test Webhook

Use Stripe CLI to test webhooks locally:

```bash
# Install Stripe CLI
brew install stripe/stripe-cli/stripe

# Login to Stripe
stripe login

# Forward webhooks to local server
stripe listen --forward-to localhost:5000/api/stripe/webhook

# Trigger test events
stripe trigger checkout.session.completed
stripe trigger payment_intent.payment_failed
```

### 3. Verify Webhook

Check webhook logs:
```sql
SELECT event_type, processed, error_message, created_at
FROM stripe_webhook_log
ORDER BY created_at DESC
LIMIT 10;
```

---

## Testing

### Test Cards

Use these test cards in development:

| Card Number         | Scenario             | Description                  |
|---------------------|----------------------|------------------------------|
| 4242 4242 4242 4242 | Success              | Payment succeeds             |
| 4000 0000 0000 0002 | Declined             | Card declined                |
| 4000 0000 0000 9995 | Insufficient funds   | Insufficient funds error     |
| 4000 0025 0000 3155 | Requires auth        | 3D Secure authentication     |

**Card Details for Testing:**
- **Expiry:** Any future date (e.g., 12/25)
- **CVC:** Any 3 digits (e.g., 123)
- **ZIP:** Any 5 digits (e.g., 12345)

### Test Workflow

1. **Create Escrow Payment:**
   ```bash
   curl -X POST https://yourdomain.com/api/stripe/create-checkout-session \
     -H "Content-Type: application/json" \
     -H "Cookie: session=your_session_cookie" \
     -d '{
       "gig_id": 1,
       "amount": 500
     }'
   ```

2. **Complete Payment:**
   - Use the returned `checkout_url`
   - Enter test card details
   - Complete checkout

3. **Verify Escrow:**
   ```bash
   curl https://yourdomain.com/api/escrow/1 \
     -H "Cookie: session=your_session_cookie"
   ```

4. **Test Refund:**
   ```bash
   curl -X POST https://yourdomain.com/api/escrow/1/refund \
     -H "Content-Type: application/json" \
     -H "Cookie: session=your_session_cookie" \
     -d '{
       "refund_amount": 250,
       "reason": "Test partial refund"
     }'
   ```

---

## Production Deployment

### Pre-Deployment Checklist

- [ ] Switch to live Stripe keys
- [ ] Configure production webhook endpoint
- [ ] Enable HTTPS on your domain
- [ ] Test webhook signature verification
- [ ] Set up Stripe monitoring alerts
- [ ] Configure logging and error tracking
- [ ] Review Stripe account settings
- [ ] Test payment flow end-to-end

### Security Best Practices

1. **Never expose secret keys:**
   - Store keys in environment variables only
   - Never commit keys to version control
   - Rotate keys if compromised

2. **Webhook Security:**
   - Always verify webhook signatures
   - Use HTTPS for webhook endpoints
   - Monitor failed webhook attempts

3. **PCI Compliance:**
   - Never store card numbers
   - Use Stripe.js for card input
   - Never log sensitive data

### Monitoring

Monitor these metrics in Stripe Dashboard:

- **Payment Success Rate:** Should be >95%
- **Refund Rate:** Monitor for unusual patterns
- **Webhook Delivery:** Should be 100%
- **Failed Payments:** Investigate failures

Set up alerts for:
- Multiple failed payments from same user
- High refund volume
- Webhook failures
- Disputed charges

---

## API Endpoints

### Payment Endpoints

#### Create Checkout Session
```
POST /api/stripe/create-checkout-session
```
**Body:**
```json
{
  "gig_id": 123,
  "amount": 500
}
```
**Response:**
```json
{
  "success": true,
  "checkout_url": "https://checkout.stripe.com/...",
  "session_id": "cs_test_...",
  "fee_breakdown": {
    "gig_amount": 500,
    "platform_fee": 75,
    "processing_fee": 15.50,
    "total_charge": 515.50,
    "freelancer_receives": 425
  }
}
```

#### Refund Escrow
```
POST /api/escrow/{gig_id}/refund
```
**Body:**
```json
{
  "refund_amount": 250,
  "reason": "Client requested partial refund"
}
```
**Response:**
```json
{
  "message": "Partial escrow refund successful via Stripe",
  "refund_id": "re_...",
  "refund_amount": 250,
  "is_partial": true
}
```

### Payment Methods

#### List Saved Cards
```
GET /api/stripe/payment-methods
```
**Response:**
```json
{
  "payment_methods": [
    {
      "id": "pm_...",
      "card": {
        "brand": "visa",
        "last4": "4242",
        "exp_month": 12,
        "exp_year": 2025
      }
    }
  ]
}
```

#### Create Setup Intent (Add Card)
```
POST /api/stripe/setup-intent
```
**Response:**
```json
{
  "client_secret": "seti_..._secret_..."
}
```

#### Delete Payment Method
```
DELETE /api/stripe/payment-methods/{payment_method_id}
```
**Response:**
```json
{
  "message": "Payment method deleted successfully"
}
```

---

## Troubleshooting

### Common Issues

#### 1. "Stripe is not configured" Error

**Cause:** Missing or invalid Stripe keys

**Solution:**
```bash
# Check environment variables
echo $STRIPE_SECRET_KEY
echo $STRIPE_PUBLISHABLE_KEY

# Verify keys are set in application
python -c "import os; print(os.environ.get('STRIPE_SECRET_KEY'))"
```

#### 2. Webhook Signature Verification Failed

**Cause:** Wrong webhook secret or payload tampering

**Solution:**
```bash
# Verify webhook secret is correct
stripe listen --print-secret

# Update .env with correct secret
STRIPE_WEBHOOK_SECRET=whsec_...
```

#### 3. Payment Succeeds But Escrow Not Funded

**Cause:** Webhook not received or processed

**Solution:**
```sql
-- Check webhook logs
SELECT * FROM stripe_webhook_log
WHERE event_type = 'checkout.session.completed'
ORDER BY created_at DESC;

-- Check escrow status
SELECT id, status, payment_reference, payment_gateway
FROM escrow
WHERE payment_reference = 'cs_test_...';
```

#### 4. Refund Fails

**Cause:** Payment already refunded or expired

**Solution:**
```python
# Check Stripe Dashboard for payment status
# Verify payment_intent ID in escrow.payment_reference

# Check refund amount doesn't exceed available
SELECT amount, refunded_amount, (amount - refunded_amount) as remaining
FROM escrow WHERE id = 123;
```

### Debug Mode

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# In app.py, add more detailed logs
app.logger.setLevel(logging.DEBUG)
```

### Support Resources

- **Stripe Documentation:** https://stripe.com/docs
- **Stripe Support:** https://support.stripe.com
- **API Reference:** https://stripe.com/docs/api
- **Webhook Guide:** https://stripe.com/docs/webhooks
- **Test Cards:** https://stripe.com/docs/testing

---

## Security Notes

### Critical Security Requirements

1. **NEVER** expose secret keys in client-side code
2. **ALWAYS** verify webhook signatures
3. **NEVER** trust client-side amount values
4. **ALWAYS** use HTTPS in production
5. **NEVER** log sensitive payment data

### Compliance

- PCI DSS Level 1 certified (handled by Stripe)
- Stripe.js for secure card input
- No card data touches your servers
- Webhook signature verification required

---

## Support

For issues or questions:

1. Check this documentation
2. Review Stripe Dashboard logs
3. Check webhook logs in database
4. Contact Stripe support for payment-specific issues

---

**Last Updated:** 2025-12-29
**Stripe API Version:** 2024-11-20.acacia
