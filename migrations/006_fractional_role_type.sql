-- Add primary sub-role type to user fractional profile
-- Values match the fractional sub-role slugs: fractional-cfo, fractional-cmo, etc.

ALTER TABLE "user" ADD COLUMN IF NOT EXISTS fractional_role_type VARCHAR(30);

-- SQLite equivalent (run this instead if using SQLite):
-- ALTER TABLE user ADD COLUMN fractional_role_type TEXT;
