-- Migration: Add Milestone Payment Support
-- Description: Adds payment_type to gig table and creates milestone and milestone_payment tables
-- Date: 2026-01-10
-- This migration is idempotent and safe to run multiple times

-- ============================================================================
-- POSTGRESQL VERSION
-- ============================================================================

-- Add payment_type column to gig table
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='gig' AND column_name='payment_type') THEN
        ALTER TABLE gig ADD COLUMN payment_type VARCHAR(20) DEFAULT 'full_payment';
    END IF;
END $$;

-- Create milestone table
CREATE TABLE IF NOT EXISTS milestone (
    id SERIAL PRIMARY KEY,
    gig_id INTEGER NOT NULL REFERENCES gig(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    amount FLOAT NOT NULL,
    "order" INTEGER NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    due_date TIMESTAMP,
    completed_at TIMESTAMP,
    approved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create milestone_payment table
CREATE TABLE IF NOT EXISTS milestone_payment (
    id SERIAL PRIMARY KEY,
    milestone_id INTEGER NOT NULL REFERENCES milestone(id) ON DELETE CASCADE,
    escrow_number VARCHAR(50) UNIQUE NOT NULL,
    gig_id INTEGER NOT NULL REFERENCES gig(id) ON DELETE CASCADE,
    client_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    freelancer_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    amount FLOAT NOT NULL,
    platform_fee FLOAT DEFAULT 0.0,
    net_amount FLOAT NOT NULL,
    status VARCHAR(30) DEFAULT 'pending',
    payment_reference VARCHAR(100),
    payment_gateway VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    funded_at TIMESTAMP,
    released_at TIMESTAMP,
    refunded_at TIMESTAMP
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_milestone_gig_id ON milestone(gig_id);
CREATE INDEX IF NOT EXISTS idx_milestone_status ON milestone(status);
CREATE INDEX IF NOT EXISTS idx_milestone_order ON milestone(gig_id, "order");
CREATE INDEX IF NOT EXISTS idx_milestone_payment_milestone_id ON milestone_payment(milestone_id);
CREATE INDEX IF NOT EXISTS idx_milestone_payment_gig_id ON milestone_payment(gig_id);
CREATE INDEX IF NOT EXISTS idx_milestone_payment_status ON milestone_payment(status);
CREATE INDEX IF NOT EXISTS idx_milestone_payment_escrow_number ON milestone_payment(escrow_number);
CREATE INDEX IF NOT EXISTS idx_gig_payment_type ON gig(payment_type);

-- Add comment explaining the feature
COMMENT ON COLUMN gig.payment_type IS 'Payment type: full_payment or milestone';
COMMENT ON TABLE milestone IS 'Tracks milestones for gigs with milestone-based payments';
COMMENT ON TABLE milestone_payment IS 'Tracks escrow payments for individual milestones';
