# Instant Payouts - Quick Start Checklist ⚡

Get instant payouts working in 15 minutes!

## ☑️ Prerequisites

- [ ] Stripe account created at https://dashboard.stripe.com
- [ ] Business verified for Malaysia
- [ ] Flask app running

---

## 🚀 5-Minute Setup

### 1️⃣ Get Stripe Keys (2 min)

```bash
# Go to: https://dashboard.stripe.com/test/apikeys
# Copy these keys (Test Mode first):

STRIPE_TEST_SECRET_KEY=sk_test_...
STRIPE_TEST_PUBLISHABLE_KEY=pk_test_...
```

### 2️⃣ Update .env File (1 min)

```bash
# Add to .env:
STRIPE_MODE=test
STRIPE_TEST_SECRET_KEY=sk_test_YOUR_KEY
STRIPE_TEST_PUBLISHABLE_KEY=pk_test_YOUR_KEY
STRIPE_TEST_WEBHOOK_SECRET=whsec_test_YOUR_SECRET  # Get in step 4
```

### 3️⃣ Enable Stripe Connect (5 min)

1. Go to https://dashboard.stripe.com/connect/settings
2. Click **Enable Express accounts**
3. Set platform name: **GigHala**

**IMPORTANT**: Complete Platform Profile (or you'll get "review responsibilities" error)
4. Go to https://dashboard.stripe.com/settings/connect/platform-profile
5. Fill in:
   - Platform info (name, website, support email)
   - **Loss Liability**: Select "Platform assumes liability" (recommended)
   - **Verification**: Select "Standard verification"
   - **Payout schedule**: Select "Manual"
6. Click **Save profile**

7. Go back to Connect → **Payouts** section
8. Enable **Instant payouts** for **Malaysia (MYR)**

### 4️⃣ Setup Webhooks (2 min)

1. Go to https://dashboard.stripe.com/test/webhooks
2. Click **Add endpoint**
3. URL: `https://your-ngrok.ngrok.io/api/stripe/webhook`
4. Select events:
   - `payout.paid`
   - `payout.failed`
   - `checkout.session.completed`
   - `payment_intent.payment_failed`
   - `charge.refunded`
5. Click **Add endpoint**
6. Copy **Signing secret** (whsec_...)
7. Add to `.env` as `STRIPE_TEST_WEBHOOK_SECRET`

### 5️⃣ Run Migration (1 min)

```bash
python3 migrations/run_stripe_connect_migration.py
```

### 6️⃣ Restart App (30 sec)

```bash
# Reload environment variables
source .env

# Restart Flask
python3 app.py
```

---

## ✅ Test It Works (5 min)

### Quick Test Flow:

1. **Add test balance**:
   ```sql
   UPDATE wallets SET balance = 500.00 WHERE user_id = 1;
   ```

2. **Login to GigHala** → Go to **Billing**

3. **Click "Request Payout"**
   - Should see "Set Up Instant Payouts" button

4. **Click "Set Up Instant Payouts"**
   - Redirects to Stripe onboarding
   - Use test bank: `000123456789`
   - Complete verification

5. **Request instant payout**:
   - Back to Billing → "Request Payout"
   - Should see "⚡ Instant Payout Available"
   - Enter amount: RM 100
   - Review fees: ~RM 6 total
   - Submit

6. **Verify payout**:
   - Check email for confirmation
   - Check Stripe Dashboard → Connect → Payouts
   - Status should be "paid" (in test mode)

7. **Trigger webhook** (if using Stripe CLI):
   ```bash
   stripe trigger payout.paid
   ```

8. **Check completion**:
   - Payout status → "completed"
   - Email received
   - Wallet updated

---

## 🎯 Go Live Checklist

When ready for production:

- [ ] Complete Stripe business verification
- [ ] Get live API keys from https://dashboard.stripe.com/apikeys
- [ ] Add live keys to `.env`
- [ ] Create live webhook endpoint (use HTTPS!)
- [ ] Update `.env`: `STRIPE_MODE=live`
- [ ] Restart application
- [ ] Test with small real payout
- [ ] Monitor logs and webhooks

---

## 🆘 Quick Troubleshooting

| Issue | Solution |
|-------|----------|
| "Review responsibilities of managing losses" | Complete Platform Profile: https://dashboard.stripe.com/settings/connect/platform-profile → Select "Platform assumes liability" |
| "Instant payouts not enabled" | Complete Stripe onboarding, add Malaysian bank account |
| "Webhook not received" | Check signing secret in `.env`, verify URL accessible |
| "Stripe payout failed" | Check Stripe Dashboard → Logs for details |
| "Onboarding link expired" | Click "Set Up Instant Payouts" again (24h expiry) |

---

## 📊 What Happens Behind the Scenes?

```
User clicks "Request Payout"
    ↓
Frontend calls /api/stripe/connect/instant-payout
    ↓
Backend validates balance & fees
    ↓
Stripe API creates payout (method='instant')
    ↓
Payout saved to DB (status='processing')
    ↓
User receives confirmation email
    ↓
[~30 minutes later]
    ↓
Stripe sends payout.paid webhook
    ↓
Backend updates status to 'completed'
    ↓
User receives completion email
    ✅ Funds in bank account!
```

---

## 💰 Fee Structure

| Payout Type | Speed | Stripe Fee | Platform Fee | Total Fee (RM 100) |
|-------------|-------|------------|--------------|-------------------|
| **Instant** | ~30 min | RM 2.00 + 2% | 2% | RM 6.00 |
| **Standard** | 3-5 days | RM 0 | 2% | RM 2.00 |

---

## 🔗 Quick Links

- **Full Setup Guide**: `/docs/INSTANT_PAYOUTS_SETUP_GUIDE.md`
- **Technical Docs**: `/STRIPE_INSTANT_PAYOUTS.md`
- **Stripe Dashboard**: https://dashboard.stripe.com
- **Stripe Docs**: https://stripe.com/docs/connect/instant-payouts

---

## ✨ You're Done!

Instant payouts are now enabled! Users can:
- Set up their Stripe Connect account
- Request instant payouts (~30 min)
- Track payout history
- Receive email notifications

**Announce it to users and watch adoption grow! 🚀**
