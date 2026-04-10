-- Migration 010: Add PDPA explicit consent tracking columns to user table
-- PDPA 2010 s.6 requires informed, explicit consent with an auditable record.
-- Run this BEFORE deploying the code that references these columns.

BEGIN;

ALTER TABLE "user"
    ADD COLUMN IF NOT EXISTS privacy_consent        BOOLEAN   NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS privacy_consent_date   TIMESTAMP,
    ADD COLUMN IF NOT EXISTS privacy_policy_version VARCHAR(10) DEFAULT '1.0';

-- Backfill: existing users are treated as having consented (they registered before
-- explicit tracking was added). Set their consent date to NOW() as a conservative
-- audit record. You may adjust this date to the actual deployment date.
UPDATE "user"
SET privacy_consent        = TRUE,
    privacy_consent_date   = NOW(),
    privacy_policy_version = '1.0'
WHERE privacy_consent = FALSE;

COMMIT;
