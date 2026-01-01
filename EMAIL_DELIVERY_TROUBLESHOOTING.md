# Email Delivery Troubleshooting Guide

## Problem: Emails Accepted by Brevo but Not Received

If you see logs showing "Email sent successfully" with message IDs, but recipients don't receive the emails, this guide will help you fix the issue.

### Understanding the Problem

When Brevo's API returns a `message_id`, it means:
- ✅ Your API request was valid
- ✅ Brevo accepted the email into their system
- ❌ **BUT** this does NOT guarantee delivery to recipients

The email might not be delivered if there are configuration issues with your Brevo account.

## Quick Diagnostic

Run the diagnostic script to identify configuration issues:

```bash
python diagnose_brevo.py
```

This script will check:
1. Environment variables are set correctly
2. API key is valid
3. Sender email is verified
4. Account status and configuration

## Common Causes and Solutions

### 1. Sender Email Not Verified (Most Common)

**Problem**: Brevo requires sender emails to be verified before they can send emails.

**Solution**:

1. Log in to [Brevo Dashboard](https://app.brevo.com/)
2. Navigate to **Senders & IP** → **Senders**
3. Click **Add a new sender**
4. Enter your sender email (the value of `BREVO_FROM_EMAIL`)
5. Check your email inbox for a 6-digit verification code
6. Enter the code in Brevo to verify the sender
7. Wait for the sender to show as "Active"

**How to check**: Look for "Active: true" next to your sender email in the Brevo dashboard.

### 2. Account in Sandbox/Test Mode

**Problem**: New Brevo accounts might be in test mode where emails are accepted but not actually sent.

**Solution**:

1. Check your account status in the Brevo dashboard
2. Make sure your account is fully activated (not in trial/test mode)
3. Complete any required account verification steps

### 3. Domain Not Authenticated

**Problem**: Without domain authentication (SPF/DKIM), emails may be rejected by recipient servers or go to spam.

**Solution**:

1. Go to **Senders & IP** → **Domains**
2. Click **Authenticate a domain**
3. Enter your domain (e.g., `gighala.com`)
4. Add the provided SPF and DKIM records to your domain's DNS settings
5. Wait for DNS propagation (can take up to 48 hours)
6. Verify the domain in Brevo

**DNS Records to Add**:
- **SPF Record**: TXT record for domain root
- **DKIM Record**: TXT record with specific key provided by Brevo

### 4. Daily Sending Limit Reached

**Problem**: Free Brevo accounts have a daily limit of 300 emails.

**Solution**:

1. Check your sending statistics in the Brevo dashboard
2. Wait until the next day if limit is reached
3. Consider upgrading your plan if you need higher limits

### 5. Recipient Email Issues

**Problem**: Recipient email addresses might be invalid, blocked, or have full inboxes.

**Solution**:

1. Go to **Transactional** → **Logs** in Brevo dashboard
2. Look for specific error messages for each recipient
3. Common issues:
   - Bounced emails (invalid address)
   - Blocked by recipient server
   - Marked as spam

## Verification Checklist

Use this checklist to ensure everything is configured correctly:

- [ ] Environment variables set in `.env`:
  - [ ] `BREVO_API_KEY` (get from Brevo dashboard)
  - [ ] `BREVO_FROM_EMAIL` (must be verified)
  - [ ] `BREVO_FROM_NAME` (optional, defaults to "GigHala")

- [ ] Brevo account setup:
  - [ ] Account is fully activated (not in trial mode)
  - [ ] Sender email is added and verified
  - [ ] Sender shows as "Active" in dashboard
  - [ ] Daily sending limit not exceeded

- [ ] Domain configuration (recommended):
  - [ ] Domain authenticated in Brevo
  - [ ] SPF record added to DNS
  - [ ] DKIM record added to DNS
  - [ ] DNS records verified (wait 24-48 hours after adding)

- [ ] Testing:
  - [ ] Run `python diagnose_brevo.py` successfully
  - [ ] Send test email through diagnostic script
  - [ ] Check test email arrives in inbox (not spam)

## Step-by-Step Fix Guide

### Step 1: Run Diagnostics

```bash
cd /home/user/GigHala
python diagnose_brevo.py
```

Review the output and note any errors or warnings.

### Step 2: Verify Sender Email

This is the **most important step** and fixes 90% of delivery issues:

1. Open [Brevo Dashboard](https://app.brevo.com/)
2. Go to **Senders & IP** → **Senders**
3. Check if your sender email is listed
4. If not listed or not verified:
   - Click **Add a new sender**
   - Enter email and name
   - Check email for verification code
   - Complete verification
5. Ensure sender shows **Active: true**

### Step 3: Check Transactional Logs

1. Go to **Transactional** → **Logs**
2. Find your recent email sends
3. Check the status of each email:
   - **Sent**: Successfully delivered
   - **Delivered**: Confirmed received by recipient server
   - **Bounced**: Failed delivery (check reason)
   - **Blocked**: Rejected by recipient server
   - **Deferred**: Temporary delay, will retry

### Step 4: Send Test Email

Using the diagnostic script:

```bash
python diagnose_brevo.py
```

When prompted, send a test email to yourself. Check:
- Email arrives in inbox (not spam)
- From address shows correctly
- Content displays properly

### Step 5: Check Spam Folder

Even with correct configuration, initial emails might go to spam:

1. Check recipient spam/junk folders
2. If found in spam, mark as "Not Spam"
3. This helps train spam filters for future emails

### Step 6: Authenticate Domain (Recommended)

For better deliverability and reputation:

1. Go to **Senders & IP** → **Domains**
2. Click **Authenticate a domain**
3. Follow instructions to add DNS records
4. Wait 24-48 hours for DNS propagation
5. Verify domain authentication

## Monitoring Email Delivery

### Application Logs

Check your application logs for diagnostic messages:

```bash
tail -f /var/log/gighala/app.log
# or wherever your logs are stored
```

Look for the diagnostic section after email sending:

```
============================================================
IMPORTANT: Emails accepted by Brevo API
If recipients don't receive emails, check:
  1. Sender email (xxx@domain.com) is VERIFIED in Brevo dashboard
  2. Account is not in sandbox/test mode
  3. Domain has SPF/DKIM records configured
  4. Brevo transactional logs: https://app.brevo.com/email/logs
  5. Run 'python diagnose_brevo.py' for detailed diagnostics
============================================================
```

### Brevo Dashboard

Regularly monitor:

1. **Transactional → Logs**: View individual email status
2. **Statistics → Email**: Overall delivery metrics
3. **Senders & IP**: Sender reputation and status

## Still Having Issues?

If emails still aren't being delivered after following this guide:

### 1. Check Brevo Status

Visit [Brevo Status Page](https://status.brevo.com/) to check for service outages.

### 2. Review API Response

Check application logs for the message ID and look it up in Brevo's transactional logs.

### 3. Contact Brevo Support

If you've verified everything and emails still aren't delivering:

1. Go to Brevo dashboard → Support
2. Provide them with:
   - Message IDs from logs
   - Timestamp of failed deliveries
   - Recipient email addresses
   - Screenshots of error messages

### 4. Test with Different Recipients

Try sending to:
- Gmail address
- Outlook/Hotmail address
- Your domain email

If it works for some but not others, the issue is likely with specific recipient servers.

## Advanced Troubleshooting

### Enable Detailed API Logging

To see the full API request/response, add debug logging to `email_service.py`:

```python
# Add at the top of send_bulk_email method
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check API Key Permissions

Ensure your API key has the correct permissions:

1. Go to **SMTP & API** → **API Keys**
2. Click on your API key
3. Ensure it has permission for "Transactional emails"

### Verify Network Connectivity

Ensure your server can reach Brevo's API:

```bash
curl -X GET "https://api.brevo.com/v3/account" \
  -H "api-key: YOUR_API_KEY"
```

Should return account information if connection is working.

## Prevention: Best Practices

### 1. Warm Up Your Sender Reputation

- Start with small volumes
- Gradually increase sending volume
- Maintain consistent sending patterns

### 2. Monitor Bounce Rates

- Keep bounce rate below 5%
- Remove invalid email addresses
- Use email validation before sending

### 3. Avoid Spam Triggers

- Don't use ALL CAPS in subject lines
- Avoid spam trigger words
- Ensure proper HTML formatting
- Include unsubscribe link for bulk emails

### 4. Maintain Good List Hygiene

- Only send to users who opted in
- Remove inactive/bounced addresses
- Honor unsubscribe requests immediately

### 5. Regular Monitoring

- Check Brevo dashboard daily
- Monitor delivery rates
- Review bounce and complaint reports

## Resources

- [Brevo API Documentation](https://developers.brevo.com/docs/send-a-transactional-email)
- [Brevo Sender Guidelines](https://help.brevo.com/hc/en-us/articles/115000188150)
- [Email Deliverability Best Practices](https://help.brevo.com/hc/en-us/sections/360002866800)
- [SPF and DKIM Setup Guide](https://help.brevo.com/hc/en-us/articles/115000197950)

## Quick Reference

### Common Commands

```bash
# Run diagnostics
python diagnose_brevo.py

# Check application logs
tail -f /var/log/gighala/app.log

# Test email service
python test_email_digest.py

# Check environment variables
env | grep BREVO
```

### Important URLs

- Brevo Dashboard: https://app.brevo.com/
- Transactional Logs: https://app.brevo.com/email/logs
- Sender Management: https://app.brevo.com/settings/sender
- API Keys: https://app.brevo.com/settings/keys/api

### Support Contacts

- Brevo Support: https://help.brevo.com/
- Brevo Community: https://community.brevo.com/
- Brevo Status: https://status.brevo.com/

---

**Last Updated**: January 2026
**Related Documents**:
- [BREVO_MIGRATION.md](BREVO_MIGRATION.md) - Migration from SendGrid to Brevo
- [SCHEDULED_EMAIL_DIGEST.md](SCHEDULED_EMAIL_DIGEST.md) - Scheduled email functionality
