-- fractional employment feature: 2025
-- creates a dedicated application table for fractional/retained role listings
-- status values: 'pending', 'shortlisted', 'accepted', 'rejected'

CREATE TABLE IF NOT EXISTS fractional_application (
    id SERIAL PRIMARY KEY,
    gig_id INTEGER NOT NULL REFERENCES gig(id) ON DELETE CASCADE,
    applicant_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    cover_note TEXT,
    proposed_monthly_rate NUMERIC(12,2),
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(gig_id, applicant_id)
);
