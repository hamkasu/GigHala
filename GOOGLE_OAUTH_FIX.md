# Fix Google OAuth Redirect URI Mismatch Error

## Problem
You're seeing: **"Error 400: redirect_uri_mismatch"** from Google

This means the redirect URL your app is sending doesn't match what's registered in Google Cloud Console.

## Solution

### For Testing on Replit (Development)

Your Replit app uses this redirect URL:
```
https://405be5ca-7330-4147-8775-c386116c19fc-00-3uvqikvn1rqfw.kirk.replit.dev/api/auth/google/callback
```

**Steps:**
1. Go to https://console.cloud.google.com/apis/credentials
2. Click your OAuth 2.0 Client ID
3. Under **Authorized redirect URIs**, add:
   ```
   https://405be5ca-7330-4147-8775-c386116c19fc-00-3uvqikvn1rqfw.kirk.replit.dev/api/auth/google/callback
   ```
4. Click **Save**
5. Copy your **Client ID** and **Client Secret**
6. Add to Replit Secrets:
   - `GOOGLE_OAUTH_CLIENT_ID` = your client ID
   - `GOOGLE_OAUTH_CLIENT_SECRET` = your client secret
7. Restart the app

### For Railway Deployment (Production)

Your Railway app will use this format:
```
https://your-app-name.railway.app/api/auth/google/callback
```

**Steps:**
1. In Google Cloud Console, add your Railway redirect URL:
   ```
   https://your-app-name.railway.app/api/auth/google/callback
   ```
2. Replace `your-app-name` with your actual Railway app name
3. Click **Save**
4. In Railway environment settings, add:
   - `GOOGLE_OAUTH_CLIENT_ID`
   - `GOOGLE_OAUTH_CLIENT_SECRET`
5. Deploy - Google Sign-In will work automatically

## Important Notes

- **Must be HTTPS** - Google OAuth only works over HTTPS
- **Exact match required** - The URL must match exactly, including the path `/api/auth/google/callback`
- **No localhost** - You can't use `http://localhost:5000` for OAuth
- **Railway auto-redirects** - Railway automatically provides HTTPS

## After Fixed

Once you've updated Google Cloud Console and restarted:
1. The "Sign up with Google" button will work
2. Users can sign in with their Google accounts
3. New user accounts are created automatically

## Troubleshooting

| Error | Solution |
|-------|----------|
| `redirect_uri_mismatch` | The callback URL in your app doesn't match Google Cloud Console |
| `invalid_client` | Wrong Client ID or Client Secret |
| `access_denied` | User cancelled the Google sign-in |
| Empty app after clicking Google button | Check browser console for errors |

## File Structure

- `app.py` - Contains OAuth routes: `/api/auth/google` and `/api/auth/google/callback`
- `google_auth.py` - Reference OAuth implementation (not used, kept for documentation)
- `requirements.txt` - Includes Authlib for OAuth handling

## Environment Variables

```bash
GOOGLE_OAUTH_CLIENT_ID=your_client_id_from_google
GOOGLE_OAUTH_CLIENT_SECRET=your_client_secret_from_google
SESSION_SECRET=your_session_encryption_key
DATABASE_URL=postgresql://user:pass@host/db
```

## Testing Google OAuth

1. Click "Sign up with Google" button on homepage
2. You'll be redirected to Google's login page
3. After authentication, you'll be redirected back to `/api/auth/google/callback`
4. If successful, you'll see the dashboard
5. If error, check browser console (F12) for details

Good luck! 🚀
