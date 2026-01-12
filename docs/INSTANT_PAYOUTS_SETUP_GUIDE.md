# GigHala Instant Payouts - Complete Setup Guide

## 📋 Overview

This guide will walk you through enabling **Instant Payouts** (Bayaran Segera) for GigHala in Malaysia. Freelancers will be able to receive their earnings in ~30 minutes instead of waiting 3-5 days.

**What's Already Done:**
- ✅ All code implemented (API endpoints, webhooks, UI)
- ✅ Database schema ready
- ✅ Fee calculations configured (RM 2.00 + 2%)
- ✅ Email/SMS notifications
- ✅ Full documentation

**What You Need to Do:**
- 🔧 Configure Stripe API keys
- 🔧 Set up Stripe Connect Dashboard
- 🔧 Configure webhooks
- 🔧 Run database migrations
- 🔧 Test the system

---

## 🚀 Step 1: Get Stripe API Keys

### 1.1 Create Stripe Account

1. Go to https://dashboard.stripe.com/register
2. Sign up with your business email
3. Complete business verification for Malaysia
4. Set primary currency to **MYR**

### 1.2 Get Test Mode Keys (for testing first)

1. Log in to https://dashboard.stripe.com
2. Ensure you're in **Test Mode** (toggle in top right)
3. Go to **Developers** → **API keys**
4. Copy the following:
   - **Publishable key**: Starts with `pk_test_...`
   - **Secret key**: Click "Reveal test key", starts with `sk_test_...`

### 1.3 Get Live Mode Keys (for production later)

1. Switch to **Live Mode** (toggle in top right)
2. Complete all verification requirements (Stripe will guide you)
3. Go to **Developers** → **API keys**
4. Copy:
   - **Publishable key**: Starts with `pk_live_...`
   - **Secret key**: Starts with `sk_live_...`

---

## 🔧 Step 2: Configure Environment Variables

### 2.1 Update Your .env File

Add these environment variables to your `.env` file:

```bash
# Stripe Configuration
STRIPE_MODE=test  # Use 'test' for testing, 'live' for production

# Test Mode Keys
STRIPE_TEST_SECRET_KEY=sk_test_YOUR_KEY_HERE
STRIPE_TEST_PUBLISHABLE_KEY=pk_test_YOUR_KEY_HERE
STRIPE_TEST_WEBHOOK_SECRET=whsec_test_YOUR_SECRET_HERE  # Will get this in Step 4

# Live Mode Keys (fill these when ready for production)
STRIPE_LIVE_SECRET_KEY=sk_live_YOUR_KEY_HERE
STRIPE_LIVE_PUBLISHABLE_KEY=pk_live_YOUR_KEY_HERE
STRIPE_LIVE_WEBHOOK_SECRET=whsec_live_YOUR_SECRET_HERE  # Will get this in Step 4
```

### 2.2 Verify Configuration

Run this command to verify your keys are loaded:

```bash
python3 -c "import os; from dotenv import load_dotenv; load_dotenv(); print('STRIPE_MODE:', os.getenv('STRIPE_MODE')); print('Test Key:', os.getenv('STRIPE_TEST_SECRET_KEY', 'NOT SET')[:15] + '...')"
```

---

## 🎨 Step 3: Configure Stripe Connect Dashboard

### 3.1 Enable Stripe Connect

1. Go to https://dashboard.stripe.com/connect/settings
2. Click **Get Started** on Stripe Connect
3. Select **Express** account type
4. Click **Enable Express accounts**

### 3.2 Branding Setup

1. In Connect Settings, scroll to **Branding**
2. Set **Platform name**: `GigHala`
3. Set **Brand color**: `#4F46E5` (or your brand color)
4. Upload your **logo** (recommended: 512x512px PNG)
5. Set **Support email**: `support@gighala.com`
6. Click **Save**

### 3.3 Complete Platform Profile (CRITICAL)

**Important**: You MUST complete this or account creation will fail with "Please review the responsibilities of managing losses" error.

1. Go to https://dashboard.stripe.com/settings/connect/platform-profile
2. Complete all required sections:

#### Platform Information
- **Platform name**: `GigHala`
- **Platform website**: `https://gighala.com`
- **Platform description**: `Freelance marketplace connecting clients with Malaysian service providers`
- **Customer support email**: `support@gighala.com`
- **Customer support phone**: Your support number

#### Loss Liability (Choose one)

**Option A: Platform assumes liability** (Recommended)
- ✅ Select "Platform assumes liability for losses"
- Platform handles chargebacks and disputes
- Simpler onboarding for freelancers
- Better user experience
- **Use this** for GigHala

**Option B: Connected accounts assume liability**
- Each freelancer responsible for own losses
- More complex verification required
- May slow down user onboarding

#### Verification Requirements
- Select **Standard verification** (recommended)
  - Name, DOB, address, bank details
  - ID may be required for high volumes

- Or **Enhanced verification** (if required by your industry)
  - More stringent requirements
  - Additional documentation needed

#### Payout Schedule
- Select **Manual** (GigHala already has payout request system)
- Freelancers request payouts themselves
- Platform controls timing

3. Click **Save profile**
4. Verify completion (all sections should have ✅ green checkmarks)

**Common Error**: If you see "Please review the responsibilities of managing losses", it means you haven't completed the Loss Liability section. Go back and select an option.

### 3.4 Enable Instant Payouts

1. Go to **Connect** → **Settings** → **Payouts**
2. Find **Instant payouts** section
3. Click **Enable instant payouts**
4. Select:
   - ✅ **Malaysia** (MY)
   - Currency: **MYR**
5. Review fee structure:
   - RM 2.00 fixed + 2% (Stripe's fee)
6. Click **Save**

### 3.4 Configure Redirect URLs

1. In Connect Settings, find **Integration** section
2. Add **Redirect URIs**:
   - Test: `http://localhost:5000/settings/payouts`
   - Production: `https://gighala.com/settings/payouts`
3. Click **Save**

---

## 🔔 Step 4: Set Up Webhooks

### 4.1 Create Webhook Endpoint (Test Mode)

1. Ensure you're in **Test Mode**
2. Go to **Developers** → **Webhooks**
3. Click **Add endpoint**
4. Configure:
   - **Endpoint URL**:
     - Local: `https://your-ngrok-url.ngrok.io/api/stripe/webhook`
     - Production: `https://gighala.com/api/stripe/webhook`
   - **Description**: `GigHala Instant Payouts`
   - **Events to send**: Click **Select events**

5. Select these events:
   - ✅ `checkout.session.completed`
   - ✅ `payment_intent.payment_failed`
   - ✅ `charge.refunded`
   - ✅ `payout.paid`
   - ✅ `payout.failed`

6. Click **Add events** then **Add endpoint**

### 4.2 Get Webhook Signing Secret (Test Mode)

1. Click on the webhook you just created
2. In **Signing secret** section, click **Reveal**
3. Copy the secret (starts with `whsec_...`)
4. Add to `.env` as `STRIPE_TEST_WEBHOOK_SECRET`

### 4.3 Repeat for Live Mode

1. Switch to **Live Mode**
2. Repeat steps 4.1 and 4.2
3. Use production URL: `https://gighala.com/api/stripe/webhook`
4. Save the live webhook secret as `STRIPE_LIVE_WEBHOOK_SECRET`

### 4.4 Test Webhooks Locally (Optional)

If testing locally, use Stripe CLI:

```bash
# Install Stripe CLI
# Mac: brew install stripe/stripe-cli/stripe
# Linux: https://stripe.com/docs/stripe-cli#install

# Login
stripe login

# Forward webhooks to local server
stripe listen --forward-to localhost:5000/api/stripe/webhook

# In another terminal, trigger test events
stripe trigger payout.paid
stripe trigger payout.failed
```

---

## 💾 Step 5: Run Database Migrations

### 5.1 Check Current Schema

```bash
# Connect to your database and check if Stripe fields exist
python3 -c "
from app import db, User, Payout
import inspect

print('User model fields:')
for field in ['stripe_account_id', 'stripe_account_status', 'stripe_onboarding_completed', 'instant_payout_enabled']:
    has_field = hasattr(User, field)
    print(f'  {field}: {'✅' if has_field else '❌'}')

print('\nPayout model fields:')
for field in ['is_instant', 'stripe_payout_id', 'estimated_arrival']:
    has_field = hasattr(Payout, field)
    print(f'  {field}: {'✅' if has_field else '❌'}')
"
```

### 5.2 Run Migration (if needed)

If fields are missing, run the migration:

```bash
python3 migrations/run_stripe_connect_migration.py
```

Expected output:
```
Running Stripe Connect migration...
✅ Added stripe_account_id to users table
✅ Added stripe_account_status to users table
✅ Added stripe_onboarding_completed to users table
✅ Added instant_payout_enabled to users table
✅ Added is_instant to payouts table
✅ Added stripe_payout_id to payouts table
✅ Created indexes
Migration completed successfully!
```

### 5.3 Verify Migration

```bash
# Check database directly (adjust for your DB)
# PostgreSQL:
psql -d gighala -c "\d users" | grep stripe
psql -d gighala -c "\d payouts" | grep -E "(is_instant|stripe)"

# MySQL:
mysql -D gighala -e "DESCRIBE users;" | grep stripe
mysql -D gighala -e "DESCRIBE payouts;" | grep -E "(is_instant|stripe)"
```

---

## 🧪 Step 6: Test the System

### 6.1 Start Your Application

```bash
# Ensure environment variables are loaded
source .env  # or use your preferred method

# Start Flask app
python3 app.py
```

### 6.2 Test User Flow

1. **Create a test user account** (or use existing)
2. **Add funds to wallet**:
   ```bash
   # Via admin panel or SQL:
   UPDATE wallets SET balance = 500.00 WHERE user_id = YOUR_USER_ID;
   ```

3. **Navigate to Billing page**: `http://localhost:5000/billing`

4. **Click "Request Payout"** button

5. **Check Stripe Connect status**:
   - If not set up, should see "Set Up Instant Payouts" button
   - Click it to start onboarding

6. **Complete Stripe onboarding**:
   - Use test bank account: `000123456789` (Stripe test account for MY)
   - Complete all verification steps
   - Should redirect back to `/settings/payouts?success=true`

7. **Request instant payout**:
   - Go back to Billing page
   - Click "Request Payout" again
   - Should now see "⚡ Instant Payout Available" badge
   - Select amount (e.g., RM 100.00)
   - Review fees:
     - Stripe fee: RM 2.00 + RM 2.00 (2%) = RM 4.00
     - Platform fee: RM 2.00
     - Net: RM 94.00
   - Submit request

8. **Verify payout created**:
   - Check email for confirmation
   - Check Stripe Dashboard → Connect → Payouts
   - Should see payout with status "paid" (in test mode)

9. **Trigger webhook** (if using Stripe CLI):
   ```bash
   stripe trigger payout.paid
   ```

10. **Check completion**:
    - Payout status should update to "completed"
    - Should receive completion email
    - Wallet balance updated

### 6.3 Test Failed Payout

```bash
# Trigger failed payout webhook
stripe trigger payout.failed
```

Verify:
- Payout status changes to "failed"
- Funds returned to wallet balance
- Failure email sent

### 6.4 Test API Endpoints Directly

```bash
# 1. Create Stripe Connect account
curl -X POST http://localhost:5000/api/stripe/connect/account \
  -H "Content-Type: application/json" \
  -b "session_cookie_here"

# 2. Get account link
curl -X POST http://localhost:5000/api/stripe/connect/account-link \
  -H "Content-Type: application/json" \
  -b "session_cookie_here"

# 3. Check account status
curl -X GET http://localhost:5000/api/stripe/connect/account-status \
  -H "Content-Type: application/json" \
  -b "session_cookie_here"

# 4. Create instant payout
curl -X POST http://localhost:5000/api/stripe/connect/instant-payout \
  -H "Content-Type: application/json" \
  -d '{"amount": 100.00}' \
  -b "session_cookie_here"
```

---

## 🚀 Step 7: Go Live

### 7.1 Pre-Launch Checklist

- [ ] Completed Stripe business verification
- [ ] All live mode API keys configured in `.env`
- [ ] Live webhook endpoint created and verified
- [ ] Tested instant payouts in test mode
- [ ] Reviewed fee structure with accounting team
- [ ] Prepared customer support documentation
- [ ] Set up monitoring/alerts for webhook failures
- [ ] HTTPS enabled on production domain

### 7.2 Switch to Live Mode

1. Update `.env`:
   ```bash
   STRIPE_MODE=live
   ```

2. Restart application:
   ```bash
   # Restart your Flask app
   sudo systemctl restart gighala  # or your restart command
   ```

3. Verify in admin panel:
   - Go to Admin → Settings → Stripe
   - Should show "Mode: Live"

### 7.3 Monitor First Payouts

1. Watch webhook logs:
   ```bash
   tail -f logs/security.log | grep -i payout
   ```

2. Check Stripe Dashboard for live payouts

3. Verify email notifications sent

4. Monitor user feedback

---

## 📊 Step 8: Admin Management

### 8.1 View Stripe Mode

```bash
# API endpoint
curl http://localhost:5000/api/admin/settings/stripe-mode
```

### 8.2 Switch Between Test/Live (Admin Only)

Through admin panel or API:

```bash
# Switch to live
curl -X POST http://localhost:5000/api/admin/settings/stripe-mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "live"}' \
  -b "admin_session_cookie"

# Switch to test
curl -X POST http://localhost:5000/api/admin/settings/stripe-mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "test"}' \
  -b "admin_session_cookie"
```

### 8.3 View Payout Reports

1. Go to Admin → Billing → Payouts
2. Filter by:
   - Status: completed, processing, failed
   - Date range
   - Instant vs Standard payouts
3. Export to CSV if needed

---

## 🔍 Troubleshooting

### Issue: "Please review the responsibilities of managing losses"

**Error**: When creating Stripe Connect accounts, you get: `Request req_xxx: Please review the responsibilities of managing losses for connected accounts at https://dashboard.stripe.com/settings/connect/platform-profile`

**Solution:**
1. This means your Platform Profile is incomplete
2. Go to https://dashboard.stripe.com/settings/connect/platform-profile
3. Complete all required sections:
   - **Platform Information**: Fill in name, website, support details
   - **Loss Liability**: Select "Platform assumes liability" (recommended for GigHala)
   - **Verification Requirements**: Select "Standard verification"
   - **Payout Schedule**: Select "Manual"
4. Click **Save profile**
5. Verify all sections have green checkmarks
6. Try creating account again

**Why this happens**: Stripe requires you to explicitly decide who handles chargebacks and fraud losses before you can create connected accounts.

### Issue: "Instant payouts not enabled"

**Solution:**
1. Check Stripe Connect onboarding completed
2. Verify Malaysian bank account added in Stripe
3. Check `instant_payout_enabled` field in database
4. Call `/api/stripe/connect/account-status` to refresh status

### Issue: "Stripe payout failed"

**Solution:**
1. Check Stripe Dashboard → Logs for error details
2. Common causes:
   - Insufficient balance in Stripe account
   - Bank account verification pending
   - Account restricted (compliance issue)
3. Funds automatically returned to user wallet
4. User receives email with failure reason

### Issue: "Webhook not received"

**Solution:**
1. Verify webhook URL is accessible (use `curl` to test)
2. Check webhook signing secret matches `.env`
3. Review Stripe Dashboard → Webhooks → Logs
4. Ensure HTTPS enabled (required in production)
5. Check firewall not blocking Stripe IPs

### Issue: "Onboarding link expired"

**Solution:**
- Account links expire in 24 hours
- User can regenerate via "Set Up Instant Payouts" button
- Call `/api/stripe/connect/account-link` again

### Issue: "Fees incorrect"

**Verify calculation:**
```python
# Example: RM 100 instant payout
gross_amount = 100.00
stripe_fixed_fee = 2.00
stripe_variable_fee = gross_amount * 0.02  # 2%
platform_fee = gross_amount * 0.02  # 2%
total_fees = stripe_fixed_fee + stripe_variable_fee + platform_fee
net_amount = gross_amount - total_fees

# Result:
# gross_amount = 100.00
# stripe_fixed_fee = 2.00
# stripe_variable_fee = 2.00
# platform_fee = 2.00
# total_fees = 6.00
# net_amount = 94.00
```

---

## 📱 User Communication

### Announcing the Feature

**Email Template:**

```
Subject: 🎉 Bayaran Segera Kini Tersedia! (Instant Payouts Now Available!)

Hi [Name],

Kami dengan gembira mengumumkan bayaran segera (instant payouts) kini tersedia di GigHala!

✨ Kelebihan:
• Terima pendapatan dalam ~30 minit (bukan 3-5 hari)
• Tiada had minimum
• Selamat dan terjamin oleh Stripe
• Mudah untuk setup

💰 Bayaran:
• Yuran Stripe: RM 2.00 + 2%
• Yuran platform: 2%

🚀 Cara Mengaktifkan:
1. Pergi ke halaman Billing
2. Klik "Request Payout"
3. Klik "Set Up Instant Payouts"
4. Lengkapkan pengesahan akaun bank
5. Mula terima bayaran segera!

Sebarang soalan? Hubungi support@gighala.com

Terima kasih,
Pasukan GigHala
```

### In-App Notification

Add to billing page or dashboard:

```
🎉 NEW: Bayaran Segera tersedia! Terima pendapatan anda dalam ~30 minit.
[Set Up Now] [Learn More]
```

---

## 📈 Monitoring & Analytics

### Key Metrics to Track

1. **Adoption Rate**:
   - % of users with instant payouts enabled
   - % of payouts using instant vs standard

2. **Success Rate**:
   - % of instant payouts completed successfully
   - Average time to completion
   - Failure rate and reasons

3. **Financial**:
   - Total instant payout volume (MYR)
   - Total fees collected
   - Average payout amount

4. **Technical**:
   - Webhook success rate
   - API response times
   - Error rates

### Query Examples

```sql
-- Instant payout adoption rate
SELECT
  COUNT(CASE WHEN instant_payout_enabled = TRUE THEN 1 END) as enabled_users,
  COUNT(*) as total_users,
  ROUND(COUNT(CASE WHEN instant_payout_enabled = TRUE THEN 1 END) * 100.0 / COUNT(*), 2) as adoption_rate
FROM users
WHERE stripe_account_id IS NOT NULL;

-- Instant payout success rate (last 30 days)
SELECT
  COUNT(*) as total_payouts,
  COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
  COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed,
  ROUND(COUNT(CASE WHEN status = 'completed' THEN 1 END) * 100.0 / COUNT(*), 2) as success_rate
FROM payouts
WHERE is_instant = TRUE
  AND requested_at >= NOW() - INTERVAL '30 days';

-- Total instant payout volume
SELECT
  COUNT(*) as total_payouts,
  SUM(amount) as total_gross,
  SUM(fee) as total_fees,
  SUM(net_amount) as total_net
FROM payouts
WHERE is_instant = TRUE
  AND status = 'completed'
  AND requested_at >= NOW() - INTERVAL '30 days';
```

---

## 🔐 Security Best Practices

1. **Protect Webhook Endpoint**:
   - Always verify signature (already implemented)
   - Use HTTPS in production
   - Rate limit webhook endpoint

2. **Secure API Keys**:
   - Never commit keys to git
   - Use environment variables
   - Rotate keys periodically
   - Restrict key permissions in Stripe

3. **Balance Validation**:
   - Always verify sufficient wallet balance
   - Prevent race conditions with transactions
   - Monitor for unusual payout patterns

4. **Audit Logs**:
   - All financial operations logged (already implemented)
   - Review security logs regularly
   - Alert on suspicious activity

5. **User Verification**:
   - Stripe handles KYC (Know Your Customer)
   - Monitor account verification status
   - Flag unusual account activity

---

## 📚 Additional Resources

- [Stripe Connect Documentation](https://stripe.com/docs/connect)
- [Stripe Instant Payouts Guide](https://stripe.com/docs/payouts#instant-payouts)
- [Stripe Connect Express](https://stripe.com/docs/connect/express-accounts)
- [Malaysia Payment Methods](https://stripe.com/docs/payments/payment-methods/overview#malaysia)
- [Stripe API Reference](https://stripe.com/docs/api/payouts)
- [Webhook Best Practices](https://stripe.com/docs/webhooks/best-practices)

---

## ✅ Setup Complete!

Once you've completed all steps, users can:

1. Enable instant payouts in their settings
2. Request instant payouts from their wallet balance
3. Receive funds in ~30 minutes to their Malaysian bank account
4. Track all payouts in their billing history

**Next Steps:**
- Announce the feature to users
- Monitor adoption and success rates
- Gather user feedback
- Consider future enhancements (auto-payouts, scheduling, etc.)

---

**Questions or Issues?**
- Technical: Check `/home/user/GigHala/STRIPE_INSTANT_PAYOUTS.md`
- Stripe Support: https://support.stripe.com
- GigHala Support: support@gighala.com

**Last Updated:** January 2026
