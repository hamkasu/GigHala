# GigHala Documentation

Welcome to GigHala's documentation! This folder contains guides and technical documentation for various features.

## 📚 Available Documentation

### Instant Payouts (Bayaran Segera)

Enable freelancers to receive their earnings in ~30 minutes via Stripe Connect:

- **[Quick Start Guide](INSTANT_PAYOUTS_QUICK_START.md)** ⚡
  - Get instant payouts working in 15 minutes
  - Step-by-step checklist
  - **Start here** if you want to get up and running quickly

- **[Complete Setup Guide](INSTANT_PAYOUTS_SETUP_GUIDE.md)** 📖
  - Comprehensive setup instructions
  - Production deployment guide
  - Troubleshooting and monitoring
  - Use this for full understanding and production deployment

- **[Technical Documentation](../STRIPE_INSTANT_PAYOUTS.md)** 🔧
  - Implementation details
  - API endpoints reference
  - Database schema
  - For developers who want to understand the code

### Configuration Files

- **[.env.stripe.example](../.env.stripe.example)**
  - Example Stripe configuration
  - Copy and fill in your API keys
  - Includes helpful comments and instructions

### Verification Tools

- **[verify_instant_payouts.py](../scripts/verify_instant_payouts.py)**
  - Automated configuration checker
  - Verifies all components are properly set up
  - Run before going live: `python3 scripts/verify_instant_payouts.py`

---

## 🚀 Quick Links

| Task | Document | Time |
|------|----------|------|
| **Setup instant payouts** | [Quick Start](INSTANT_PAYOUTS_QUICK_START.md) | 15 min |
| **Go live to production** | [Setup Guide](INSTANT_PAYOUTS_SETUP_GUIDE.md) | 1 hour |
| **Understand the code** | [Technical Docs](../STRIPE_INSTANT_PAYOUTS.md) | - |
| **Troubleshoot issues** | [Setup Guide - Troubleshooting](INSTANT_PAYOUTS_SETUP_GUIDE.md#-troubleshooting) | - |
| **Verify configuration** | Run `python3 scripts/verify_instant_payouts.py` | 2 min |

---

## 💡 Common Questions

### What are Instant Payouts?

Instant Payouts allow Malaysian freelancers to receive their GigHala earnings in approximately 30 minutes instead of waiting 3-5 business days. It's powered by Stripe Connect and supports Malaysian bank accounts and MYR currency.

### How much does it cost?

- **Instant Payout**: RM 2.00 + 2% (Stripe fee) + 2% (platform fee)
- **Standard Payout**: 2% (platform fee only), 3-5 days

Example: RM 100 instant payout → ~RM 6 in fees → User receives RM 94 in ~30 minutes

### Is it already implemented?

**Yes!** All the code is already implemented in GigHala. You just need to:
1. Configure Stripe API keys
2. Enable Stripe Connect in your dashboard
3. Set up webhooks
4. Run database migrations

Follow the [Quick Start Guide](INSTANT_PAYOUTS_QUICK_START.md) to get it working.

### How do I test it?

1. Use Stripe Test Mode keys
2. Complete the test setup in [Quick Start](INSTANT_PAYOUTS_QUICK_START.md)
3. Use Stripe CLI to trigger webhook events:
   ```bash
   stripe listen --forward-to localhost:5000/api/stripe/webhook
   stripe trigger payout.paid
   ```

### How do I go live?

Follow the **"Go Live Checklist"** in the [Setup Guide](INSTANT_PAYOUTS_SETUP_GUIDE.md#-step-7-go-live).

Key steps:
1. Complete Stripe business verification
2. Get live API keys
3. Update `.env` with live keys
4. Set `STRIPE_MODE=live`
5. Create live webhook endpoint
6. Test with small amounts first

---

## 🆘 Getting Help

### Documentation Issues

If something in the docs is unclear:
1. Check the [Setup Guide Troubleshooting](INSTANT_PAYOUTS_SETUP_GUIDE.md#-troubleshooting)
2. Run the verification script: `python3 scripts/verify_instant_payouts.py`
3. Review Stripe Dashboard logs

### Technical Issues

- **Stripe API Issues**: https://support.stripe.com
- **GigHala Support**: support@gighala.com
- **Stripe Documentation**: https://stripe.com/docs/connect/instant-payouts

### Common Issues

| Issue | Solution |
|-------|----------|
| "Instant payouts not enabled" | Complete Stripe onboarding, add Malaysian bank |
| "Webhook not received" | Check signing secret, verify URL accessible |
| "Payout failed" | Check Stripe Dashboard logs for error details |
| "API key invalid" | Verify correct mode (test/live) and key format |

---

## 📝 Contributing

When updating documentation:

1. Keep the Quick Start simple and concise
2. Put detailed explanations in the Setup Guide
3. Put code details in Technical Documentation
4. Test all commands and instructions
5. Update this README if adding new docs

---

## 📅 Last Updated

- **Instant Payouts Documentation**: January 2026
- **Implementation Status**: ✅ Complete and ready for production

---

## ✨ Feature Status

| Feature | Status | Documentation |
|---------|--------|---------------|
| Instant Payouts (Malaysia) | ✅ Implemented | [Quick Start](INSTANT_PAYOUTS_QUICK_START.md) |
| Standard Payouts | ✅ Implemented | See `app.py` billing endpoints |
| Stripe Connect Onboarding | ✅ Implemented | [Setup Guide](INSTANT_PAYOUTS_SETUP_GUIDE.md) |
| Webhook Handling | ✅ Implemented | [Technical Docs](../STRIPE_INSTANT_PAYOUTS.md) |
| Email/SMS Notifications | ✅ Implemented | See notification system in `app.py` |

---

**Ready to get started? → [Quick Start Guide](INSTANT_PAYOUTS_QUICK_START.md)** 🚀
