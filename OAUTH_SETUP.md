# Social Login Setup Guide

This document explains how to set up social login (Google, Apple, Microsoft) for GigHala.

## Overview

We've implemented OAuth 2.0 authentication for three providers:
- **Google Sign-In**
- **Apple Sign In**
- **Microsoft Account**

## Database Migration

First, apply the database migration to add OAuth support:

```bash
# For PostgreSQL
psql -d your_database_name -f migrations/add_oauth_support.sql

# Or if using DATABASE_URL
psql $DATABASE_URL -f migrations/add_oauth_support.sql
```

This migration:
- Adds `oauth_provider` column (google, apple, microsoft, or null)
- Adds `oauth_id` column (user ID from OAuth provider)
- Makes `password_hash` nullable (OAuth users don't have passwords)
- Creates an index for faster OAuth lookups

## Provider Setup

### 1. Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the **Google+ API**
4. Go to **Credentials** → **Create Credentials** → **OAuth 2.0 Client ID**
5. Configure the OAuth consent screen
6. Set authorized redirect URIs:
   - `http://localhost:5000/api/auth/google/callback` (development)
   - `https://yourdomain.com/api/auth/google/callback` (production)
7. Copy your **Client ID** and **Client Secret**

### 2. Microsoft OAuth Setup

1. Go to [Azure Portal](https://portal.azure.com/)
2. Navigate to **Azure Active Directory** → **App registrations**
3. Click **New registration**
4. Set redirect URI:
   - `http://localhost:5000/api/auth/microsoft/callback` (development)
   - `https://yourdomain.com/api/auth/microsoft/callback` (production)
5. Go to **Certificates & secrets** → Create a new client secret
6. Copy your **Application (client) ID** and **Client Secret**

### 3. Apple Sign In Setup

1. Go to [Apple Developer](https://developer.apple.com/)
2. Navigate to **Certificates, Identifiers & Profiles**
3. Create a new **App ID** or use an existing one
4. Enable **Sign in with Apple** capability
5. Create a **Services ID** for web authentication
6. Configure redirect URLs:
   - `http://localhost:5000/api/auth/apple/callback` (development)
   - `https://yourdomain.com/api/auth/apple/callback` (production)
7. Create a **Key** for Sign in with Apple
8. Download the private key (.p8 file)
9. Copy your **Services ID**, **Team ID**, **Key ID**, and save the private key file

## Environment Configuration

Add these variables to your `.env` file:

```bash
# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id-here
GOOGLE_CLIENT_SECRET=your-google-client-secret-here

# Apple Sign In
APPLE_CLIENT_ID=your-apple-services-id-here
APPLE_TEAM_ID=your-apple-team-id-here
APPLE_KEY_ID=your-apple-key-id-here
APPLE_PRIVATE_KEY_PATH=/path/to/AuthKey_XXXXXXXXXX.p8

# Microsoft OAuth
MICROSOFT_CLIENT_ID=your-microsoft-client-id-here
MICROSOFT_CLIENT_SECRET=your-microsoft-client-secret-here
```

## Installation

Install the required OAuth library:

```bash
pip install -r requirements.txt
```

## How It Works

### User Flow

1. User clicks on a social login button (Google, Apple, or Microsoft)
2. User is redirected to the OAuth provider's login page
3. User authorizes the application
4. OAuth provider redirects back to the callback URL with authorization code
5. Backend exchanges code for user information
6. System checks if user exists:
   - **If email exists**: Links OAuth provider to existing account
   - **If new user**: Creates new account with OAuth info
7. User is logged in and redirected to dashboard

### Account Linking

- If a user registers with email/password and later uses social login with the same email, the accounts are automatically linked
- OAuth users have `oauth_provider` and `oauth_id` set
- Regular users have these fields as `null`
- OAuth users cannot login with password (they must use their OAuth provider)

### Security Features

- Email is automatically verified for OAuth users (providers verify emails)
- OAuth users are created with `is_verified=True`
- Username is auto-generated from email with random suffix
- User type defaults to 'both' (freelancer and client)
- IC/Passport number is NOT required for OAuth users (can be added later in profile)

## API Endpoints

### OAuth Initiation
- `GET /api/auth/google` - Initiate Google OAuth
- `GET /api/auth/microsoft` - Initiate Microsoft OAuth
- `GET /api/auth/apple` - Initiate Apple OAuth

### OAuth Callbacks
- `GET /api/auth/google/callback` - Google OAuth callback
- `GET /api/auth/microsoft/callback` - Microsoft OAuth callback
- `GET /api/auth/apple/callback` - Apple OAuth callback

## Frontend Integration

Social login buttons are already integrated into:
- Login modal (`templates/index.html`)
- Register modal (`templates/index.html`)

The buttons use simple links that redirect to OAuth endpoints:

```html
<a href="/api/auth/google" class="btn-social btn-google">Google</a>
<a href="/api/auth/microsoft" class="btn-social btn-microsoft">Microsoft</a>
<a href="/api/auth/apple" class="btn-social btn-apple">Apple</a>
```

## Testing

### Development Testing

1. Start your Flask app:
   ```bash
   python app.py
   ```

2. Navigate to `http://localhost:5000`
3. Click on Login or Register
4. Try one of the social login buttons

### Common Issues

**"redirect_uri_mismatch"**
- Check that your redirect URIs in OAuth provider settings match exactly
- Include protocol (http/https), domain, port, and path

**"invalid_client"**
- Verify CLIENT_ID and CLIENT_SECRET are correct
- Check environment variables are loaded

**"missing user data"**
- Ensure OAuth scopes include email and profile
- Check that user granted all required permissions

## Production Deployment

1. Update redirect URIs in all OAuth provider consoles to use your production domain
2. Update `.env` with production credentials
3. Ensure HTTPS is enabled (required by most OAuth providers)
4. Set `FLASK_ENV=production`
5. Restart your application

## Support

For issues or questions:
- Check error logs in the application
- Review OAuth provider documentation
- Contact your development team

## Security Notes

- Never commit OAuth credentials to version control
- Keep `.env` file secure and out of git (already in `.gitignore`)
- Use HTTPS in production
- Regularly rotate OAuth secrets
- Monitor for suspicious OAuth activity
