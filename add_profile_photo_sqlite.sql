-- SQLite Migration: Add profile_photo column to user table
-- Run this against your SQLite database to enable user profile photo uploads.

-- 1. Add the profile_photo column to the user table
-- NOTE: SQLite does not support IF NOT EXISTS for ALTER TABLE ADD COLUMN
--       Run only if the column does not already exist.
ALTER TABLE user ADD COLUMN profile_photo VARCHAR(255);

-- 2. Verify the change
PRAGMA table_info(user);

-- Notes:
-- - The profile_photo column stores the filename (not full path) of the uploaded image.
-- - Files are stored in uploads/profile_photos/ on the server.
-- - The URL to serve the photo is: /uploads/profile_photos/<profile_photo>
-- - Allowed image types: PNG, JPG, JPEG, GIF, WEBP (max 5 MB)

-- Example manual update queries:

-- Clear profile photo for a specific user (replace 123 with the user ID):
-- UPDATE user SET profile_photo = NULL WHERE id = 123;

-- Set a profile photo manually (replace values accordingly):
-- UPDATE user SET profile_photo = 'filename.jpg' WHERE id = 123;

-- View all users with profile photos:
-- SELECT id, username, full_name, profile_photo FROM user WHERE profile_photo IS NOT NULL;

-- View all users WITHOUT profile photos:
-- SELECT id, username, full_name FROM user WHERE profile_photo IS NULL;

-- Count users with and without photos:
-- SELECT
--     COUNT(CASE WHEN profile_photo IS NOT NULL THEN 1 END) AS with_photo,
--     COUNT(CASE WHEN profile_photo IS NULL THEN 1 END) AS without_photo
-- FROM user;
