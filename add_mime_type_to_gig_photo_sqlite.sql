-- SQLite Migration to add mime_type column to gig_photo table
-- This allows tracking of different file types (images, PDFs, Word documents)
-- Execute this in your SQLite database

-- 1. Add mime_type column to gig_photo table
ALTER TABLE gig_photo ADD COLUMN mime_type VARCHAR(100);

-- 2. Update existing records to set mime_type based on file extension
UPDATE gig_photo
SET mime_type = CASE
    WHEN LOWER(filename) LIKE '%.png' THEN 'image/png'
    WHEN LOWER(filename) LIKE '%.jpg' OR LOWER(filename) LIKE '%.jpeg' THEN 'image/jpeg'
    WHEN LOWER(filename) LIKE '%.webp' THEN 'image/webp'
    WHEN LOWER(filename) LIKE '%.gif' THEN 'image/gif'
    WHEN LOWER(filename) LIKE '%.pdf' THEN 'application/pdf'
    WHEN LOWER(filename) LIKE '%.doc' THEN 'application/msword'
    WHEN LOWER(filename) LIKE '%.docx' THEN 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    ELSE 'image/jpeg'
END
WHERE mime_type IS NULL;

-- 3. Verify the changes
SELECT id, filename, original_filename, mime_type, created_at
FROM gig_photo
LIMIT 5;

-- Notes:
-- - mime_type stores the MIME type of uploaded files
-- - Supports: image/png, image/jpeg, image/webp, image/gif, application/pdf,
--   application/msword, application/vnd.openxmlformats-officedocument.wordprocessingml.document
-- - This enables proper display/download handling in the frontend
