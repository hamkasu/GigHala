-- Migration for adding scoring system features and bilingual support
-- This script adds the necessary database changes for the review/rating system and language preferences

-- Add review_count column to User table
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS review_count INTEGER DEFAULT 0;

-- Add language preference column to User table (ms = Malay, en = English)
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS language VARCHAR(5) DEFAULT 'ms';

-- Add updated_at column to Review table
ALTER TABLE review ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Create unique constraint for reviews (one review per gig per reviewer)
-- Note: This will fail if duplicate reviews already exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'unique_review_per_gig'
    ) THEN
        ALTER TABLE review ADD CONSTRAINT unique_review_per_gig UNIQUE (gig_id, reviewer_id);
    END IF;
END $$;

-- Update existing users' review counts based on existing reviews
UPDATE "user"
SET review_count = (
    SELECT COUNT(*)
    FROM review
    WHERE review.reviewee_id = "user".id
)
WHERE EXISTS (
    SELECT 1
    FROM review
    WHERE review.reviewee_id = "user".id
);

-- Update existing users' ratings based on existing reviews
UPDATE "user"
SET rating = (
    SELECT ROUND(AVG(review.rating)::numeric, 2)
    FROM review
    WHERE review.reviewee_id = "user".id
)
WHERE EXISTS (
    SELECT 1
    FROM review
    WHERE review.reviewee_id = "user".id
);
