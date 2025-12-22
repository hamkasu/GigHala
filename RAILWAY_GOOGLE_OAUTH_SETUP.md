# GigHala Google Sign-In Setup for Railway Deployment

## Overview
Your GigHala platform now has full Google OAuth integration for user authentication. This guide explains how to set it up on Railway.

## Prerequisites
- Railway account (https://railway.app)
- Google Cloud project with OAuth 2.0 credentials
- Your Railway app URL (e.g., `https://your-app-name.railway.app`)

## Step 1: Set Up Google OAuth Credentials

1. Go to **Google Cloud Console**: https://console.cloud.google.com/apis/credentials
2. Create a new OAuth 2.0 Client ID (Web application)
3. Add your Railway app's redirect URL to **Authorized redirect URIs**:
   ```
   https://your-app-name.railway.app/google_login/callback
   ```
4. Copy your **Client ID** and **Client Secret**

## Step 2: Configure Environment Variables on Railway

In your Railway project settings, add these environment variables:

```
GOOGLE_OAUTH_CLIENT_ID=your_client_id_here
GOOGLE_OAUTH_CLIENT_SECRET=your_client_secret_here
SESSION_SECRET=generate_a_random_secure_string_here
DATABASE_URL=your_postgresql_connection_string
STRIPE_SECRET_KEY=your_stripe_key_if_using_payments
```

## Step 3: Deploy to Railway

1. Connect your GitHub repository to Railway
2. Railway will automatically detect your `railway.json` configuration
3. The app will use the `gunicorn` command specified in `railway.json`
4. Deploy! Your app will start with Google Sign-In enabled

## Step 4: Test Google Sign-In

1. Visit your Railway app URL: `https://your-app-name.railway.app`
2. Click the **"Sign up with Google"** button
3. Authenticate with your Google account
4. You should be redirected to the app dashboard after successful login

## How It Works

- Users click the Google sign-in button on the homepage
- The app redirects to Google's OAuth authorization endpoint
- After authorization, Google redirects back to `/google_login/callback`
- The app automatically creates a user account with their Google email and name
- User session is established with Flask-Login

## Important Notes

- **HTTPS Required**: Google OAuth only works over HTTPS. Railway provides HTTPS by default.
- **Redirect URL**: Make sure the redirect URL in Google Cloud matches your Railway app URL exactly
- **Secrets Management**: Never commit credentials to Git. Railway's environment variable system keeps them secure.
- **Session Secret**: Generate a strong random string for `SESSION_SECRET` - this encrypts user sessions

## Troubleshooting

### "Invalid OAuth Client"
- Check that your Client ID and Client Secret are correct
- Verify the redirect URL matches exactly in Google Cloud Console

### "Redirect URI mismatch"
- Make sure your Railway app URL is added to Google's authorized redirect URIs
- Include the full path: `https://your-app-name.railway.app/google_login/callback`

### Users can't log in
- Check Railway logs: Railway Dashboard → Your Project → Deployments → Logs
- Verify all environment variables are set correctly
- Check that your PostgreSQL database is connected and running

## What's Included

The Google OAuth implementation includes:

1. **Flask-Login Integration**: Manages user sessions securely
2. **OAuth Blueprint**: Handles login/callback routes
3. **User Model**: Stores OAuth provider info and user data
4. **Automatic Account Creation**: Creates user accounts on first login
5. **Halal Compliance**: User location and verification tracking
6. **Bilingual Support**: Malay/English language preferences

## File Structure

- `google_auth.py` - OAuth blueprint with login/callback routes
- `app.py` - Main app configuration with Flask-Login setup
- `railway.json` - Railway deployment configuration
- `requirements.txt` - Python dependencies including Flask-Login and oauthlib

## Next Steps

After deployment:
1. Customize the user profile fields in the dashboard
2. Add location-based gig matching
3. Set up Stripe for payment processing
4. Configure SOCSO compliance features

For full platform documentation, see the other guides in your repository.
