-- Migration 009: Widen columns for Fernet-encrypted PII (PDPA compliance)
-- Run BEFORE deploying the code that uses EncryptedString columns.
-- After running this SQL, run migrations/009_encrypt_data.py to encrypt
-- all existing plain-text values.
--
-- Fernet tokens for short strings (~20 chars) are ~120–160 chars.
-- TEXT is used to eliminate length concerns entirely.

BEGIN;

-- user table
ALTER TABLE "user"
    ALTER COLUMN phone         TYPE TEXT,
    ALTER COLUMN ic_number     TYPE TEXT,
    ALTER COLUMN bank_account_number TYPE TEXT,
    ALTER COLUMN bank_account_holder TYPE TEXT;

-- identity_verification table
ALTER TABLE identity_verification
    ALTER COLUMN ic_number TYPE TEXT,
    ALTER COLUMN full_name TYPE TEXT;

-- payout table
ALTER TABLE payout
    ALTER COLUMN account_number TYPE TEXT,
    ALTER COLUMN account_name   TYPE TEXT;

COMMIT;
