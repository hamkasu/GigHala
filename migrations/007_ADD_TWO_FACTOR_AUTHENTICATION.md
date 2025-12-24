# Migration 007: Add Two-Factor Authentication (2FA) Support

## Overview
This migration adds TOTP (Time-based One-Time Password) Two-Factor Authentication support to the GigHala platform to enhance account security.

## Date
2025-12-24

## Changes

### Database Schema Changes

#### User Table
Added three new columns to the `user` table:

1. **totp_secret** (VARCHAR(32))
   - Stores the Base32-encoded TOTP secret key
   - Used to generate and verify 2FA codes
   - NULL when 2FA is not set up

2. **totp_enabled** (BOOLEAN, DEFAULT FALSE)
   - Indicates whether 2FA is active for the user
   - Only set to TRUE after successful 2FA setup verification

3. **totp_enabled_at** (TIMESTAMP)
   - Timestamp when 2FA was enabled
   - Used for audit logging and compliance

### API Endpoints Added

1. **POST /api/2fa/setup/start**
   - Initiates 2FA setup
   - Generates TOTP secret and QR code
   - Requires authentication

2. **POST /api/2fa/setup/verify**
   - Completes 2FA setup
   - Verifies the TOTP code to confirm setup
   - Enables 2FA upon successful verification

3. **POST /api/2fa/verify**
   - Verifies 2FA code during login
   - Completes authentication after password validation
   - Rate-limited to prevent brute force attacks

4. **POST /api/2fa/disable**
   - Disables 2FA for a user
   - Requires both password and valid 2FA code
   - Logs security event with high severity

5. **GET /api/2fa/status**
   - Returns 2FA status for current user
   - Shows whether 2FA is enabled and when

### Security Features

1. **Login Flow Enhancement**
   - Modified `/api/login` to support 2FA verification
   - Users with 2FA enabled receive a challenge after password validation
   - Pre-authentication session expires after 5 minutes

2. **Rate Limiting**
   - 2FA verification endpoint is rate-limited (5 attempts per 15 minutes)
   - Prevents brute force attacks on 2FA codes

3. **Security Logging**
   - All 2FA events are logged via the security_logger:
     - 2FA setup initiated
     - 2FA setup verification (success/failure)
     - 2FA enabled
     - 2FA disabled
     - Login 2FA challenge issued
     - Login 2FA verification (success/failure)

4. **Clock Skew Tolerance**
   - TOTP verification allows 1 time-step window for clock differences
   - Reduces false negatives due to time synchronization issues

## Dependencies

### New Python Packages
Added to `requirements.txt`:
- **pyotp>=2.9.0** - Python library for TOTP generation and verification
- **qrcode>=7.4.2** - QR code generation for authenticator app setup

## Running the Migration

### For PostgreSQL:
```bash
psql -U <username> -d <database> -f migrations/007_add_two_factor_authentication.sql
```

### For SQLite:
```bash
sqlite3 <database_file> < migrations/007_add_two_factor_authentication_sqlite.sql
```

### Using Python migration script:
```bash
python migrations/run_migration.py
```

## Testing

### Test 2FA Setup:
1. Login to a user account
2. Call `POST /api/2fa/setup/start`
3. Scan QR code with Google Authenticator or similar app
4. Call `POST /api/2fa/setup/verify` with the TOTP code
5. Verify `totp_enabled` is set to `true`

### Test 2FA Login:
1. Logout
2. Call `POST /api/login` with valid credentials
3. Verify response contains `requires_2fa: true`
4. Call `POST /api/2fa/verify` with TOTP code from authenticator app
5. Verify successful login

### Test 2FA Disable:
1. While logged in with 2FA enabled
2. Call `POST /api/2fa/disable` with password and current TOTP code
3. Verify 2FA is disabled

## Rollback

To rollback this migration:

### PostgreSQL:
```sql
ALTER TABLE "user" DROP COLUMN IF EXISTS totp_secret;
ALTER TABLE "user" DROP COLUMN IF EXISTS totp_enabled;
ALTER TABLE "user" DROP COLUMN IF EXISTS totp_enabled_at;
DROP INDEX IF EXISTS idx_user_totp_enabled;
```

### SQLite:
```sql
-- SQLite doesn't support DROP COLUMN easily
-- Requires recreating the table without these columns
-- See migrations/007_rollback_two_factor_authentication_sqlite.sql
```

## Security Considerations

1. **Secret Storage**: TOTP secrets are stored in the database. Ensure database encryption at rest is enabled in production.

2. **Backup Codes**: This implementation does not include backup codes. Consider adding backup code generation in a future migration for account recovery.

3. **Force 2FA**: Currently 2FA is optional. Consider making it mandatory for admin accounts or high-value operations.

4. **Recovery Process**: Establish a manual account recovery process for users who lose access to their 2FA device.

## Compliance

This migration helps meet security compliance requirements:
- **PCI DSS**: Multi-factor authentication for system access
- **SOC 2**: Strong authentication controls
- **ISO 27001**: Access control and authentication policies
- **GDPR**: Security of processing (Article 32)

## Related Files
- `/home/user/GigHala/app.py` (Lines 1715-1718, 3924-3973, 4024-4302)
- `/home/user/GigHala/requirements.txt`
- `/home/user/GigHala/migrations/007_add_two_factor_authentication.sql`
- `/home/user/GigHala/migrations/007_add_two_factor_authentication_sqlite.sql`
