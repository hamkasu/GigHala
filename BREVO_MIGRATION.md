# Migration from SendGrid to Brevo

This document explains the migration from SendGrid to Brevo (formerly Sendinblue) for email services.

## What Changed

- **Email Service Provider**: Changed from SendGrid to Brevo
- **Python Package**: Changed from `sendgrid` to `brevo-python`
- **Environment Variables**: Changed from `SENDGRID_*` to `BREVO_*`

## Required Steps

### 1. Install New Package

If you're updating an existing deployment, uninstall SendGrid and install Brevo:

```bash
pip uninstall sendgrid
pip install brevo-python
```

Or simply install from the updated requirements.txt:

```bash
pip install -r requirements.txt
```

### 2. Update Environment Variables

Update your `.env` file with the new Brevo credentials:

**Remove these:**
```bash
SENDGRID_API_KEY=...
SENDGRID_FROM_EMAIL=...
```

**Add these:**
```bash
BREVO_API_KEY=your-brevo-api-key-here
BREVO_FROM_EMAIL=noreply@yourdomain.com
BREVO_FROM_NAME=GigHala
```

### 3. Get Your Brevo API Key

1. Sign up or log in to [Brevo](https://www.brevo.com/)
2. Go to **SMTP & API** → **API Keys**
3. Create a new API key or use an existing one
4. Copy the API key to your `BREVO_API_KEY` environment variable

### 4. Verify Sender Email

Make sure your sender email (`BREVO_FROM_EMAIL`) is verified in your Brevo account:

1. Go to **Senders & IP** → **Senders**
2. Add and verify your sender email address
3. Use this verified email in your environment variables

### 5. Restart Your Application

After updating environment variables, restart your application:

```bash
# If using systemd
sudo systemctl restart gighala

# If using Docker
docker-compose restart

# If running directly
# Stop the app and restart it
```

## Features Retained

All features remain the same:

✓ User-by-user progress indicators
✓ Individual email sending (BCC-style privacy)
✓ Success/failure tracking
✓ Detailed logging
✓ Admin panel email sending
✓ Scheduled digest emails

## Benefits of Brevo

- **Generous Free Tier**: 300 emails per day for free
- **Better Deliverability**: Advanced email routing
- **SMS Support**: Can also send SMS (already have Twilio, but good to have options)
- **Marketing Tools**: Includes marketing automation features
- **Better Support**: Excellent customer support

## Troubleshooting

### Error: "Brevo is not configured"

- Check that `BREVO_API_KEY` and `BREVO_FROM_EMAIL` are set in your environment
- Verify the API key is correct

### Error: 401 Unauthorized

- Your API key is invalid or expired
- Generate a new API key from Brevo dashboard

### Error: Sender email not verified

- Go to Brevo dashboard → Senders & IP → Senders
- Add and verify your sender email address

### Emails not being sent

- Check your Brevo account for any sending limits
- Verify your account is active
- Check application logs for detailed error messages

## API Compatibility

The `EmailService` class maintains the same interface:

```python
# Send single email
email_service.send_single_email(
    to_email="user@example.com",
    to_name="User Name",
    subject="Subject",
    html_content="<html>...</html>"
)

# Send bulk email
email_service.send_bulk_email(
    to_emails=[("user1@example.com", "User 1"), ("user2@example.com", "User 2")],
    subject="Subject",
    html_content="<html>...</html>"
)
```

No code changes required in other parts of the application!

## Support

For issues related to:
- **Brevo API**: Check [Brevo Documentation](https://developers.brevo.com/)
- **Application Issues**: Check application logs or contact admin

## References

- [Brevo Official Website](https://www.brevo.com/)
- [Brevo API Documentation](https://developers.brevo.com/)
- [Brevo Python SDK](https://github.com/getbrevo/brevo-python)
