# Google Sign-In Setup Instructions

Your GigHala app is ready for Google authentication! Follow these steps to enable Google Sign-In:

## Step 1: Get Your Redirect URL

Your app's redirect URL is automatically generated. Check the console logs when the app starts - it will show a message like:

```
✅ Google Authentication Setup Instructions:
1. Go to https://console.cloud.google.com/apis/credentials
2. Create a new OAuth 2.0 Client ID (Web application)
3. Add this redirect URL to Authorized redirect URIs:
   https://YOUR-REPLIT-DOMAIN/google_login/callback
```

## Step 2: Create OAuth Credentials on Google Cloud

1. Visit https://console.cloud.google.com/apis/credentials
2. Click **"Create Credentials"** → **"OAuth Client ID"**
3. Select **"Web application"**
4. Under "Authorized redirect URIs", add the URL from Step 1
5. Copy your **Client ID** and **Client Secret**

## Step 3: Add Credentials to Your App

1. In your Replit project, go to **Secrets** (key icon on the left)
2. Add two new secrets:
   - Key: `GOOGLE_OAUTH_CLIENT_ID`
   - Value: (paste your Client ID)
   
   - Key: `GOOGLE_OAUTH_CLIENT_SECRET`
   - Value: (paste your Client Secret)

## Step 4: Restart Your App

Your app will automatically pick up the credentials and enable Google Sign-In on the registration and login pages.

## What's Included

- ✅ Google OAuth button on homepage
- ✅ Automatic user account creation on first login
- ✅ Secure session management with Flask-Login
- ✅ OAuth user data stored safely in database

## Troubleshooting

**"Missing credentials" error?**
- Make sure you added the secrets exactly as `GOOGLE_OAUTH_CLIENT_ID` and `GOOGLE_OAUTH_CLIENT_SECRET`
- Restart your app after adding secrets

**Redirect URL mismatch error?**
- The URL in Google Console must match exactly (including https://)
- Check the console logs for your exact redirect URL

**Users can't complete sign-in?**
- Make sure your app is running on https (Replit automatically handles this)
- Clear browser cookies and try again

## Support

For more details on Google OAuth with Flask:
https://docs.replit.com/additional-resources/google-auth-in-flask#set-up-your-oauth-app--client
