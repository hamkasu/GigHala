-- Migration 058: Add PDPA consent tracking fields to identity_verification
-- PDPA 2010 s.7 (Notice & Choice) requires explicit, recorded consent before
-- collecting sensitive personal data such as IC/passport images.

ALTER TABLE identity_verification
    ADD COLUMN IF NOT EXISTS verification_consent      BOOLEAN   NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS verification_consent_date TIMESTAMP,
    ADD COLUMN IF NOT EXISTS consent_policy_version    VARCHAR(10) DEFAULT '1.0';

-- Backfill: existing records pre-date this requirement; mark them as legacy.
-- Admin team should re-verify any active records at next renewal if required.
UPDATE identity_verification
SET    verification_consent      = FALSE,
       consent_policy_version    = 'legacy'
WHERE  verification_consent_date IS NULL;

-- Index for audit queries (e.g. find all records missing consent)
CREATE INDEX IF NOT EXISTS idx_identity_verification_consent
    ON identity_verification (verification_consent);

COMMENT ON COLUMN identity_verification.verification_consent      IS 'PDPA s.7: user explicitly consented to biometric data processing';
COMMENT ON COLUMN identity_verification.verification_consent_date IS 'UTC timestamp when consent was given';
COMMENT ON COLUMN identity_verification.consent_policy_version    IS 'Version of privacy policy accepted; legacy = pre-PDPA enforcement';
