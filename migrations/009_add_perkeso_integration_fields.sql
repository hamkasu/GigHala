-- Migration: Add PERKESO GIG Workers API Integration Fields
-- Description: Adds fields to track PERKESO API registration status per user and
--              deduction submission/callback status per SOCSO contribution record.
--              Replaces manual ASSIST Portal workflow with automated API calls.
-- API Reference: GIG Workers API Documentation v2.1 (PERKESO, 07 May 2026)
-- Date: 2026-05-07

-- -----------------------------------------------------------------------
-- User table: PERKESO registration tracking
-- -----------------------------------------------------------------------

-- Whether this freelancer has been registered via PERKESO GIG Workers API
ALTER TABLE user ADD COLUMN perkeso_registered BOOLEAN DEFAULT FALSE;

-- Timestamp of successful PERKESO API registration
ALTER TABLE user ADD COLUMN perkeso_registration_date DATETIME;

-- PERKESO sector code assigned to this worker (e.g. 'P' = Service Provider).
-- See GET /api/v1/sectors for full list. Defaults applied at submission time.
ALTER TABLE user ADD COLUMN perkeso_sector_code VARCHAR(10);

-- -----------------------------------------------------------------------
-- socso_contribution table: deduction submission & callback tracking
-- -----------------------------------------------------------------------

-- Unique request_id sent to PERKESO with the deduction submission
ALTER TABLE socso_contribution ADD COLUMN perkeso_request_id VARCHAR(100);

-- Deduction ID returned by PERKESO in the async callback
ALTER TABLE socso_contribution ADD COLUMN perkeso_deduction_id VARCHAR(100);

-- Status from PERKESO callback: ACCEPTED | PARTIAL_ACCEPTED | REJECTED | DUPLICATE_TRANSACTION
ALTER TABLE socso_contribution ADD COLUMN perkeso_submission_status VARCHAR(50);

-- When the deduction was submitted to PERKESO API
ALTER TABLE socso_contribution ADD COLUMN perkeso_submitted_at DATETIME;

-- When the async callback was received from PERKESO
ALTER TABLE socso_contribution ADD COLUMN perkeso_callback_received_at DATETIME;

-- -----------------------------------------------------------------------
-- Indexes
-- -----------------------------------------------------------------------

CREATE INDEX idx_user_perkeso_registered ON user(perkeso_registered);
CREATE INDEX idx_socso_perkeso_request_id ON socso_contribution(perkeso_request_id);
CREATE INDEX idx_socso_perkeso_status ON socso_contribution(perkeso_submission_status);
