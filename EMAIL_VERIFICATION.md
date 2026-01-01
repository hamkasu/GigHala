# Email Verification Feature

## Overview

This document describes the email verification feature implemented for user registration in GigHala. The feature ensures that users verify their email addresses before they can access certain features of the platform.

## Features

1. **Email Validation**: Validates email format during registration using the `email-validator` library
2. **Email Verification**: Sends a verification email with a unique token to newly registered users
3. **Secure Tokens**: Uses cryptographically secure random tokens with 24-hour expiration
4. **Verification Endpoints**: Provides both GET (link-based) and POST (API) verification endpoints
5. **Resend Functionality**: Allows users to request a new verification email if needed
6. **OAuth Integration**: OAuth users (Google, Microsoft, Apple) are automatically marked as verified

## How It Works

### 1. User Registration

When a user registers with email/password:

1. Email format is validated using `email-validator`
2. A secure verification token is generated
3. Token is stored in the database with a 24-hour expiration
4. User is created with `is_verified=False`
5. A verification email is sent to the user's email address

### 2. Email Verification

Users can verify their email in two ways:

**Via Email Link (GET request):**
- Click the link in the verification email
- Format: `https://gighala.com/verify-email?token={token}`
- Automatically logs in the user after successful verification
- Redirects to dashboard with success message

**Via API (POST request):**
- Send POST request to `/api/verify-email` with token in JSON body
- Returns verification status and user details
- Useful for single-page applications

### 3. Resending Verification Email

If the verification email is not received or has expired:

- POST to `/api/resend-verification` (requires login)
- Generates a new token with fresh 24-hour expiration
- Sends a new verification email

## Database Schema

### New Fields in User Table

```sql
email_verification_token VARCHAR(100)  -- Unique verification token
email_verification_expires TIMESTAMP   -- Token expiration time (24 hours)
```

### Indexes

```sql
CREATE INDEX idx_user_email_verification_token ON user(email_verification_token);
```

## API Endpoints

### 1. Register (Modified)

**Endpoint:** `POST /api/register`

**Response:**
```json
{
  "message": "Registration successful. Please check your email to verify your account.",
  "verification_required": true,
  "user": {
    "id": 123,
    "username": "john_doe",
    "email": "john@example.com",
    "user_type": "freelancer",
    "is_verified": false
  }
}
```

### 2. Verify Email (GET)

**Endpoint:** `GET /verify-email?token={token}`

**Behavior:**
- Verifies the token
- Marks user as verified
- Logs in the user
- Redirects to `/?verified=true` on success
- Redirects to `/?verification_error={message}` on failure

### 3. Verify Email (API)

**Endpoint:** `POST /api/verify-email`

**Request:**
```json
{
  "token": "secure_random_token_here"
}
```

**Response (Success):**
```json
{
  "message": "Email verified successfully",
  "verified": true,
  "user": {
    "id": 123,
    "username": "john_doe",
    "email": "john@example.com",
    "is_verified": true
  }
}
```

**Response (Error):**
```json
{
  "error": "Invalid verification token",
  "verified": false
}
```

### 4. Resend Verification

**Endpoint:** `POST /api/resend-verification`

**Authentication:** Required (login_required)

**Response (Success):**
```json
{
  "message": "Verification email sent successfully"
}
```

**Response (Already Verified):**
```json
{
  "message": "Email already verified"
}
```

## Email Template

The verification email includes:

- Welcoming message
- Clear call-to-action button
- Plain text link as alternative
- Expiration notice (24 hours)
- Security notice (ignore if not requested)

## Security Features

1. **Secure Token Generation**: Uses `secrets.token_urlsafe(32)` for cryptographically secure tokens
2. **Token Expiration**: Tokens expire after 24 hours
3. **One-Time Use**: Tokens are cleared after successful verification
4. **Rate Limiting**: Registration endpoint has rate limiting to prevent abuse
5. **Error Handling**: Graceful error handling without exposing sensitive information

## Migration

### Running the Migration

To apply the database migration:

```bash
# Make the migration script executable
chmod +x migrations/run_email_verification_migration.py

# Run the migration
python migrations/run_email_verification_migration.py
```

The migration automatically detects your database type (PostgreSQL or SQLite) and applies the appropriate schema changes.

### Manual Migration (if needed)

**PostgreSQL:**
```bash
psql $DATABASE_URL < migrations/010_add_email_verification.sql
```

**SQLite:**
```bash
sqlite3 database.db < migrations/010_add_email_verification_sqlite.sql
```

## Environment Variables

Ensure the following environment variable is set:

```bash
APP_URL=https://gighala.com  # or http://localhost:5000 for development
```

This is used to generate the verification link in the email.

## OAuth Users

Users who register via OAuth providers (Google, Microsoft, Apple) are automatically marked as `is_verified=True` since the OAuth provider has already verified their email address.

## Testing

### Manual Testing

1. **Register a new user:**
   ```bash
   curl -X POST http://localhost:5000/api/register \
     -H "Content-Type: application/json" \
     -d '{
       "email": "test@example.com",
       "username": "testuser",
       "password": "Test1234!",
       "privacy_consent": true,
       "socso_consent": true
     }'
   ```

2. **Check email for verification link**

3. **Verify email via link:**
   ```
   http://localhost:5000/verify-email?token={token_from_email}
   ```

4. **Or verify via API:**
   ```bash
   curl -X POST http://localhost:5000/api/verify-email \
     -H "Content-Type: application/json" \
     -d '{"token": "token_from_email"}'
   ```

## Future Enhancements

Possible future improvements:

1. Configurable token expiration time
2. Email verification reminder notifications
3. Admin panel to manually verify users
4. Verification status tracking in user dashboard
5. Analytics on verification conversion rates

## Troubleshooting

### Email not received

1. Check spam/junk folder
2. Verify email service is configured correctly
3. Check application logs for email sending errors
4. Use the resend verification endpoint

### Token expired

1. Use the resend verification endpoint to get a new token
2. Tokens expire after 24 hours for security

### Migration errors

1. Ensure database connection is configured
2. Check that user table exists
3. Verify database user has ALTER TABLE permissions
4. Check migration logs for specific errors

## Related Files

- `app.py` - Main application file with verification logic
- `migrations/010_add_email_verification.sql` - PostgreSQL migration
- `migrations/010_add_email_verification_sqlite.sql` - SQLite migration
- `migrations/run_email_verification_migration.py` - Migration runner
- `email_service.py` - Email sending service

## Support

For issues or questions about email verification, please contact the development team or create an issue in the project repository.
