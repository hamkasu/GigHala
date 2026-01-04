-- Migration: Add AI moderation support to Gig table
-- Date: 2026-01-04
-- Description: Adds ai_moderation_result field to store AI halal compliance check results

-- Add ai_moderation_result column to gig table
ALTER TABLE gig
ADD COLUMN IF NOT EXISTS ai_moderation_result TEXT;

-- Add index for querying gigs flagged for review
-- This helps admins quickly find gigs that need manual review
CREATE INDEX IF NOT EXISTS idx_gig_ai_moderation
ON gig ((ai_moderation_result::jsonb->>'action'));

-- Create a view for admin dashboard to see flagged gigs
CREATE OR REPLACE VIEW ai_flagged_gigs AS
SELECT
    g.id,
    g.gig_code,
    g.title,
    g.category,
    g.created_at,
    g.ai_moderation_result,
    u.username as client_username,
    u.email as client_email
FROM gig g
JOIN "user" u ON g.client_id = u.id
WHERE g.ai_moderation_result IS NOT NULL
  AND g.ai_moderation_result::jsonb->>'action' IN ('flag', 'reject')
ORDER BY g.created_at DESC;

-- Add comment to column
COMMENT ON COLUMN gig.ai_moderation_result IS 'JSON result from AI halal compliance check using Groq API';
