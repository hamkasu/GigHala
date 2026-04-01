-- fractional employment feature: 2025
-- adds freelancer availability and retainer profile fields to the user table

ALTER TABLE "user" ADD COLUMN IF NOT EXISTS available_for_fractional BOOLEAN DEFAULT FALSE;
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS fractional_days_available NUMERIC(3,1);
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS max_concurrent_clients INTEGER;
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS min_engagement_months INTEGER;
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS monthly_retainer_rate NUMERIC(12,2);
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS fractional_industries VARCHAR(255);
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS linkedin_url VARCHAR(255);
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS years_experience INTEGER;
