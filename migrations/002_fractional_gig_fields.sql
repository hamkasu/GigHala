-- fractional employment feature: 2025
-- listing_type values: 'gig', 'fractional', 'retained'
-- rate_type values: 'monthly_retainer', 'daily_rate', 'hourly'
-- remote_onsite values: 'remote', 'onsite', 'hybrid'

ALTER TABLE gig ADD COLUMN IF NOT EXISTS listing_type VARCHAR(20) DEFAULT 'gig';
ALTER TABLE gig ADD COLUMN IF NOT EXISTS commitment_days_per_week NUMERIC(3,1);
ALTER TABLE gig ADD COLUMN IF NOT EXISTS engagement_duration_months INTEGER;
ALTER TABLE gig ADD COLUMN IF NOT EXISTS rate_type VARCHAR(20);
ALTER TABLE gig ADD COLUMN IF NOT EXISTS monthly_retainer_amount NUMERIC(12,2);
ALTER TABLE gig ADD COLUMN IF NOT EXISTS min_years_experience INTEGER;
ALTER TABLE gig ADD COLUMN IF NOT EXISTS industry_focus VARCHAR(100);
ALTER TABLE gig ADD COLUMN IF NOT EXISTS remote_onsite VARCHAR(20) DEFAULT 'onsite';
