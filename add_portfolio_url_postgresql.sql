-- PostgreSQL Migration: Add portfolio_url column to user table
-- Run this against your PostgreSQL database to allow users to save an external portfolio link.

-- 1. Add the portfolio_url column to the user table
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS portfolio_url VARCHAR(500);

-- 2. Verify the change
SELECT column_name, data_type, character_maximum_length
FROM information_schema.columns
WHERE table_name = 'user'
  AND column_name = 'portfolio_url';

-- Notes:
-- - Users enter their portfolio URL in Settings > Profil.
-- - The URL is displayed as a clickable "Lihat Portfolio" link on their public profile page.
-- - To manually set a portfolio URL for a specific user:
--     UPDATE "user" SET portfolio_url = 'https://example.com/portfolio' WHERE id = <user_id>;
-- - To clear a user's portfolio URL:
--     UPDATE "user" SET portfolio_url = NULL WHERE id = <user_id>;

-- View all users with portfolio URLs:
-- SELECT id, username, full_name, portfolio_url FROM "user" WHERE portfolio_url IS NOT NULL;
