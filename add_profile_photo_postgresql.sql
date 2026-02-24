-- PostgreSQL Migration: Add profile_photo column to user table
-- Run this against your PostgreSQL database to enable user profile photo uploads.

-- 1. Add the profile_photo column to the user table
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS profile_photo VARCHAR(255);

-- 2. Verify the change
SELECT column_name, data_type, character_maximum_length
FROM information_schema.columns
WHERE table_name = 'user'
  AND column_name = 'profile_photo';

-- 3. (Optional) Create an index for faster lookups by profile_photo
-- CREATE INDEX idx_user_profile_photo ON "user"(profile_photo) WHERE profile_photo IS NOT NULL;

-- Notes:
-- - The profile_photo column stores the filename (not full path) of the uploaded image.
-- - Files are stored in uploads/profile_photos/ on the server.
-- - The URL to serve the photo is: /uploads/profile_photos/<profile_photo>
-- - Allowed image types: PNG, JPG, JPEG, GIF, WEBP (max 5 MB)
-- - To manually clear a user's profile photo:
--     UPDATE "user" SET profile_photo = NULL WHERE id = <user_id>;
-- - To manually set a profile photo (if you have placed the file on the server):
--     UPDATE "user" SET profile_photo = '<filename>' WHERE id = <user_id>;

-- Example manual update queries:

-- Clear profile photo for a specific user (replace 123 with the user ID):
-- UPDATE "user" SET profile_photo = NULL WHERE id = 123;

-- View all users with profile photos:
-- SELECT id, username, full_name, profile_photo FROM "user" WHERE profile_photo IS NOT NULL;

-- View all users WITHOUT profile photos:
-- SELECT id, username, full_name FROM "user" WHERE profile_photo IS NULL;
