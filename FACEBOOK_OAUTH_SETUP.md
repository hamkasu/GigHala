# Facebook OAuth Setup Guide for GigHala

This guide will help you set up Facebook Login for your GigHala application.

## Prerequisites

- A Facebook account
- Your GigHala application deployed (local or production URL)

## Step 1: Create a Facebook App

1. Go to [Facebook Developers](https://developers.facebook.com/)
2. Click **"My Apps"** in the top right corner
3. Click **"Create App"**
4. Select **"Consumer"** as the app type
5. Fill in the required information:
   - **App Name**: GigHala (or your custom app name)
   - **App Contact Email**: Your email address
6. Click **"Create App"**

## Step 2: Add Facebook Login Product

1. In your app dashboard, find **"Add Products to Your App"** section
2. Locate **"Facebook Login"** and click **"Set Up"**
3. Select **"Web"** as the platform
4. Enter your Site URL (e.g., `https://yourdomain.com` or `http://localhost:5000` for local development)
5. Click **"Save"** and **"Continue"**

## Step 3: Configure OAuth Settings

1. Go to **"Facebook Login"** → **"Settings"** in the left sidebar
2. Under **"Valid OAuth Redirect URIs"**, add your callback URLs:

   **For Local Development:**
   ```
   http://localhost:5000/api/auth/facebook/callback
   ```

   **For Production:**
   ```
   https://yourdomain.com/api/auth/facebook/callback
   https://www.yourdomain.com/api/auth/facebook/callback
   ```

3. Click **"Save Changes"**

## Step 4: Get Your App Credentials

1. Go to **"Settings"** → **"Basic"** in the left sidebar
2. You'll see:
   - **App ID**: Copy this value
   - **App Secret**: Click **"Show"** and copy this value (keep it secret!)

## Step 5: Configure Environment Variables

Add the following to your `.env` file:

```env
# Facebook OAuth
FACEBOOK_CLIENT_ID=your-facebook-app-id-here
FACEBOOK_CLIENT_SECRET=your-facebook-app-secret-here
```

Replace `your-facebook-app-id-here` and `your-facebook-app-secret-here` with the values from Step 4.

## Step 6: Configure App Domain (Production Only)

1. Go to **"Settings"** → **"Basic"**
2. Scroll down to **"App Domains"**
3. Add your domain (e.g., `yourdomain.com`)
4. Click **"Save Changes"**

## Step 7: Set Privacy Policy URL (Required for Public Apps)

1. Still in **"Settings"** → **"Basic"**
2. Scroll down to **"Privacy Policy URL"**
3. Enter your privacy policy URL (e.g., `https://yourdomain.com/privacy`)
4. Click **"Save Changes"**

## Step 8: Make Your App Public (Production Only)

By default, your app is in **Development Mode** which means only you and authorized test users can log in.

**To make it public:**

1. Go to **"Settings"** → **"Basic"**
2. At the top of the page, toggle the switch from **"In Development"** to **"Live"**
3. You may need to complete additional steps like:
   - Adding a privacy policy URL
   - Selecting a category for your app
   - Providing a business use case

## Step 9: Test Facebook Login

1. Restart your Flask application
2. Navigate to your GigHala homepage
3. Click **"Log In"** or **"Register"**
4. Click **"Continue with Facebook"**
5. You should be redirected to Facebook for authentication
6. After authorizing, you should be redirected back to your dashboard

## Troubleshooting

### Error: "URL Blocked: This redirect failed because the redirect URI is not whitelisted"

**Solution:** Make sure you've added your callback URL to **"Valid OAuth Redirect URIs"** in Facebook Login Settings.

### Error: "App Not Setup: This app is still in development mode"

**Solution:** Either:
- Add your Facebook account as a test user (Settings → Roles → Test Users)
- Make your app public (see Step 8)

### Error: "facebook_email_required"

**Solution:** The user didn't grant email permission or hasn't verified their email with Facebook. Make sure:
- Your app requests the `email` permission (already configured in code)
- The user grants the email permission when logging in
- The user has a verified email on Facebook

### Email Not Returned by Facebook

Some users may not have a verified email on Facebook or may deny the email permission. Consider:
- Making email optional in your registration flow
- Prompting users to add an email after registration
- Using the Facebook ID as a unique identifier instead

## Security Best Practices

1. **Keep Your App Secret Secure**: Never commit your `.env` file to version control
2. **Use HTTPS in Production**: Facebook requires HTTPS for OAuth in production
3. **Validate Redirect URIs**: Only add legitimate callback URLs to your whitelist
4. **Review Permissions**: Only request the permissions you actually need (`email` and `public_profile`)
5. **Monitor App Activity**: Regularly check your Facebook App dashboard for suspicious activity

## Facebook API Versions

The current implementation uses Facebook Graph API v18.0. Facebook typically supports API versions for 2 years.

To update the API version:
1. Open `app.py`
2. Find the Facebook OAuth configuration (around line 231)
3. Update the version number in the URLs:
   ```python
   access_token_url='https://graph.facebook.com/v18.0/oauth/access_token',
   authorize_url='https://www.facebook.com/v18.0/dialog/oauth',
   api_base_url='https://graph.facebook.com/v18.0/',
   ```

Check [Facebook's Platform Changelog](https://developers.facebook.com/docs/graph-api/changelog/) for the latest version.

## Data Access and Privacy

Facebook Login provides access to:
- **User ID** (unique Facebook identifier)
- **Email Address** (if granted permission)
- **Full Name** (from public profile)

This data is stored in your database according to your privacy policy. Make sure to:
- Inform users about data collection
- Comply with GDPR/privacy regulations
- Allow users to delete their data

## Permissions

The app requests these permissions:
- `email`: Access to user's email address
- `public_profile`: Access to public profile information (name, profile picture)

These are configured in `app.py` at line 239:
```python
client_kwargs={
    'scope': 'email public_profile'
}
```

## Additional Resources

- [Facebook Login Documentation](https://developers.facebook.com/docs/facebook-login/)
- [Facebook Graph API Reference](https://developers.facebook.com/docs/graph-api/)
- [OAuth Best Practices](https://developers.facebook.com/docs/facebook-login/security/)

## Support

If you encounter issues:
1. Check the [Facebook Developers Community](https://developers.facebook.com/community/)
2. Review your app's error logs in the Facebook App Dashboard
3. Check your Flask application logs for detailed error messages
