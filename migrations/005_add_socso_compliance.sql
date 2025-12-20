-- Migration: Add SOCSO Compliance Support (Gig Workers Bill 2025)
-- Description: Implements mandatory SOCSO contribution tracking and deduction
-- Required by: Self-Employment Social Security Scheme (SESKSO/SKSPS)
-- Deduction Rate: 1.25% of net earnings (after platform commission)

-- =====================================================
-- 1. Update User table for SOCSO registration tracking
-- =====================================================
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS socso_registered BOOLEAN DEFAULT FALSE;
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS socso_consent BOOLEAN DEFAULT FALSE;
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS socso_consent_date TIMESTAMP;
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS socso_data_complete BOOLEAN DEFAULT FALSE;

-- Update existing users: Mark as needing SOCSO consent if they're freelancers with IC numbers
UPDATE "user"
SET socso_data_complete = TRUE
WHERE ic_number IS NOT NULL
  AND ic_number != ''
  AND (user_type = 'freelancer' OR user_type = 'both');

-- =====================================================
-- 2. Update Transaction table to track SOCSO deductions
-- =====================================================
ALTER TABLE transaction ADD COLUMN IF NOT EXISTS socso_amount FLOAT DEFAULT 0.0;

-- Comment for clarity
COMMENT ON COLUMN transaction.socso_amount IS 'SOCSO contribution deducted (1.25% of net_amount) per Gig Workers Bill 2025';

-- =====================================================
-- 3. Update Payout table to track SOCSO deductions
-- =====================================================
ALTER TABLE payout ADD COLUMN IF NOT EXISTS socso_amount FLOAT DEFAULT 0.0;

-- Comment for clarity
COMMENT ON COLUMN payout.socso_amount IS 'SOCSO contribution deducted (1.25% of amount before fees) per Gig Workers Bill 2025';

-- =====================================================
-- 4. Update PaymentHistory table to track SOCSO
-- =====================================================
ALTER TABLE payment_history ADD COLUMN IF NOT EXISTS socso_amount FLOAT DEFAULT 0.0;

-- Comment for clarity
COMMENT ON COLUMN payment_history.socso_amount IS 'SOCSO contribution amount for this transaction';

-- =====================================================
-- 5. Create SocsoContribution table for compliance tracking
-- =====================================================
CREATE TABLE IF NOT EXISTS socso_contribution (
    id SERIAL PRIMARY KEY,

    -- Worker identification
    freelancer_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,

    -- Source transaction references (one will be populated)
    transaction_id INTEGER REFERENCES transaction(id) ON DELETE SET NULL,
    payout_id INTEGER REFERENCES payout(id) ON DELETE SET NULL,
    gig_id INTEGER REFERENCES gig(id) ON DELETE SET NULL,

    -- Financial details
    gross_amount FLOAT NOT NULL,  -- Original gig amount
    platform_commission FLOAT NOT NULL,  -- Platform fee deducted
    net_earnings FLOAT NOT NULL,  -- Amount after commission, before SOCSO
    socso_amount FLOAT NOT NULL,  -- 1.25% of net_earnings
    final_payout FLOAT NOT NULL,  -- Amount after SOCSO deduction

    -- Contribution metadata
    contribution_month VARCHAR(7) NOT NULL,  -- YYYY-MM format for monthly reporting
    contribution_year INTEGER NOT NULL,
    contribution_type VARCHAR(20) NOT NULL,  -- 'escrow_release', 'payout', 'transaction'

    -- ASSIST Portal remittance tracking
    remitted_to_socso BOOLEAN DEFAULT FALSE,
    remittance_date TIMESTAMP,
    remittance_reference VARCHAR(100),  -- ASSIST Portal reference number
    remittance_batch_id VARCHAR(100),  -- Batch upload identifier

    -- Audit trail
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Notes
    notes TEXT
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_socso_freelancer ON socso_contribution(freelancer_id);
CREATE INDEX IF NOT EXISTS idx_socso_month ON socso_contribution(contribution_month);
CREATE INDEX IF NOT EXISTS idx_socso_year ON socso_contribution(contribution_year);
CREATE INDEX IF NOT EXISTS idx_socso_remitted ON socso_contribution(remitted_to_socso);
CREATE INDEX IF NOT EXISTS idx_socso_transaction ON socso_contribution(transaction_id);
CREATE INDEX IF NOT EXISTS idx_socso_payout ON socso_contribution(payout_id);
CREATE INDEX IF NOT EXISTS idx_socso_gig ON socso_contribution(gig_id);

-- Add comments for documentation
COMMENT ON TABLE socso_contribution IS 'Tracks all SOCSO contributions deducted from freelancer earnings per Gig Workers Bill 2025';
COMMENT ON COLUMN socso_contribution.gross_amount IS 'Original gig payment amount from client';
COMMENT ON COLUMN socso_contribution.platform_commission IS 'Platform fee/commission deducted';
COMMENT ON COLUMN socso_contribution.net_earnings IS 'Amount after commission but before SOCSO (basis for 1.25% calculation)';
COMMENT ON COLUMN socso_contribution.socso_amount IS 'Mandatory 1.25% SOCSO deduction';
COMMENT ON COLUMN socso_contribution.final_payout IS 'Final amount paid to freelancer after all deductions';
COMMENT ON COLUMN socso_contribution.contribution_month IS 'Month for SOCSO reporting (YYYY-MM)';
COMMENT ON COLUMN socso_contribution.remitted_to_socso IS 'Whether contribution has been remitted to ASSIST Portal';

-- =====================================================
-- 6. Create view for monthly SOCSO reporting
-- =====================================================
CREATE OR REPLACE VIEW socso_monthly_report AS
SELECT
    sc.contribution_month,
    sc.contribution_year,
    u.id as freelancer_id,
    u.full_name,
    u.ic_number,
    u.email,
    u.phone,
    COUNT(sc.id) as transaction_count,
    SUM(sc.net_earnings) as total_net_earnings,
    SUM(sc.socso_amount) as total_socso_amount,
    SUM(sc.final_payout) as total_final_payout,
    BOOL_AND(sc.remitted_to_socso) as all_remitted,
    MAX(sc.remittance_date) as last_remittance_date
FROM socso_contribution sc
JOIN "user" u ON sc.freelancer_id = u.id
GROUP BY sc.contribution_month, sc.contribution_year, u.id, u.full_name, u.ic_number, u.email, u.phone
ORDER BY sc.contribution_year DESC, sc.contribution_month DESC, u.full_name ASC;

COMMENT ON VIEW socso_monthly_report IS 'Monthly aggregated SOCSO contributions for ASSIST Portal bulk upload';

-- =====================================================
-- 7. Create function to calculate SOCSO amount
-- =====================================================
CREATE OR REPLACE FUNCTION calculate_socso(net_earnings FLOAT)
RETURNS FLOAT AS $$
BEGIN
    -- SOCSO rate: 1.25% of net earnings
    -- Round to 2 decimal places (Malaysian Ringgit sen)
    RETURN ROUND(net_earnings * 0.0125, 2);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION calculate_socso IS 'Calculates 1.25% SOCSO contribution from net earnings, rounded to sen';

-- =====================================================
-- 8. Create trigger to auto-update updated_at timestamp
-- =====================================================
CREATE OR REPLACE FUNCTION update_socso_contribution_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_socso_contribution_timestamp
BEFORE UPDATE ON socso_contribution
FOR EACH ROW
EXECUTE FUNCTION update_socso_contribution_timestamp();

-- =====================================================
-- Migration complete
-- =====================================================
-- Summary of changes:
-- 1. Added SOCSO consent/registration fields to User table
-- 2. Added socso_amount tracking to Transaction, Payout, PaymentHistory tables
-- 3. Created comprehensive SocsoContribution table for compliance audit trail
-- 4. Created monthly reporting view for ASSIST Portal exports
-- 5. Created SOCSO calculation function (1.25%)
-- 6. Added indexes for query performance
-- 7. Added documentation comments for all schema changes
