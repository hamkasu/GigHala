# SQL Migration for Worker Specializations Feature

This document contains the SQL queries needed to manually update the database to support worker specializations.

## Overview

The worker specializations feature allows workers to:
- Select multiple categories they specialize in
- Add specific skills for each category (up to 10 skills per category)
- Display their specializations on their public profile
- Manage their specializations through the settings page

## Database Changes

### New Table: `worker_specialization`

This table links workers (users) to categories with their specific skills for each category.

```sql
-- Create the worker_specialization table
CREATE TABLE worker_specialization (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    category_id INTEGER NOT NULL,
    skills TEXT,  -- JSON array of skills
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES category(id) ON DELETE CASCADE,
    UNIQUE(user_id, category_id)  -- Each user can only have one specialization per category
);
```

### Indexes for Performance

```sql
-- Create indexes for faster queries
CREATE INDEX idx_worker_specialization_user_id ON worker_specialization(user_id);
CREATE INDEX idx_worker_specialization_category_id ON worker_specialization(category_id);
```

### Update Trigger for `updated_at`

```sql
-- Create trigger to automatically update the updated_at timestamp
CREATE TRIGGER update_worker_specialization_timestamp
AFTER UPDATE ON worker_specialization
BEGIN
    UPDATE worker_specialization
    SET updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.id;
END;
```

## Migration Steps

### Step 1: Backup Your Database

**IMPORTANT**: Always backup your database before running migrations!

```bash
# If using SQLite (default for Flask apps)
cp instance/gighala.db instance/gighala.db.backup_$(date +%Y%m%d_%H%M%S)

# Or if your database is elsewhere, adjust the path accordingly
```

### Step 2: Run the Migration Queries

Connect to your database and run the queries in this order:

```sql
-- 1. Create the worker_specialization table
CREATE TABLE IF NOT EXISTS worker_specialization (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    category_id INTEGER NOT NULL,
    skills TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES category(id) ON DELETE CASCADE,
    UNIQUE(user_id, category_id)
);

-- 2. Create indexes
CREATE INDEX IF NOT EXISTS idx_worker_specialization_user_id
ON worker_specialization(user_id);

CREATE INDEX IF NOT EXISTS idx_worker_specialization_category_id
ON worker_specialization(category_id);

-- 3. Create update trigger
CREATE TRIGGER IF NOT EXISTS update_worker_specialization_timestamp
AFTER UPDATE ON worker_specialization
BEGIN
    UPDATE worker_specialization
    SET updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.id;
END;
```

### Step 3: Verify the Migration

Check that the table was created successfully:

```sql
-- Check if table exists
SELECT name FROM sqlite_master WHERE type='table' AND name='worker_specialization';

-- Check table structure
PRAGMA table_info(worker_specialization);

-- Check indexes
SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='worker_specialization';

-- Check triggers
SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name='worker_specialization';
```

Expected output for `PRAGMA table_info(worker_specialization)`:
```
cid  name          type      notnull  dflt_value             pk
---  ------------  --------  -------  ---------------------  --
0    id            INTEGER   0        NULL                   1
1    user_id       INTEGER   1        NULL                   0
2    category_id   INTEGER   1        NULL                   0
3    skills        TEXT      0        NULL                   0
4    created_at    TIMESTAMP 0        CURRENT_TIMESTAMP      0
5    updated_at    TIMESTAMP 0        CURRENT_TIMESTAMP      0
```

## Using Flask-Migrate (Alternative Method)

If you prefer using Flask-Migrate for database migrations:

```bash
# Initialize migrations (if not already done)
flask db init

# Create a new migration
flask db migrate -m "Add worker_specialization table"

# Review the generated migration file in migrations/versions/
# Then apply the migration
flask db upgrade
```

## Sample Data (Optional - For Testing)

```sql
-- Example: Add a specialization for user_id=1 in category_id=1 (assuming these exist)
INSERT INTO worker_specialization (user_id, category_id, skills)
VALUES (
    1,
    1,
    '["Logo Design", "Branding", "UI/UX Design", "Photoshop", "Illustrator"]'
);

-- Example: Add another specialization for the same user in a different category
INSERT INTO worker_specialization (user_id, category_id, skills)
VALUES (
    1,
    2,
    '["Content Writing", "Copywriting", "SEO Writing", "Blog Posts"]'
);
```

## Query Examples

### Get all specializations for a specific user

```sql
SELECT
    ws.id,
    ws.user_id,
    c.name as category_name,
    c.slug as category_slug,
    c.icon as category_icon,
    ws.skills,
    ws.created_at,
    ws.updated_at
FROM worker_specialization ws
JOIN category c ON ws.category_id = c.id
WHERE ws.user_id = 1;
```

### Get all users specialized in a specific category

```sql
SELECT
    u.id,
    u.username,
    u.full_name,
    ws.skills
FROM worker_specialization ws
JOIN user u ON ws.user_id = u.id
WHERE ws.category_id = 1;
```

### Count specializations per category

```sql
SELECT
    c.name as category_name,
    COUNT(ws.id) as worker_count
FROM category c
LEFT JOIN worker_specialization ws ON c.id = ws.category_id
GROUP BY c.id, c.name
ORDER BY worker_count DESC;
```

## Rollback (If Needed)

If you need to rollback the migration:

```sql
-- Drop the trigger first
DROP TRIGGER IF EXISTS update_worker_specialization_timestamp;

-- Drop the indexes
DROP INDEX IF EXISTS idx_worker_specialization_user_id;
DROP INDEX IF EXISTS idx_worker_specialization_category_id;

-- Drop the table
DROP TABLE IF EXISTS worker_specialization;
```

**Note**: This will permanently delete all worker specialization data!

## API Endpoints Added

The following API endpoints are now available:

- `GET /api/specializations` - Get all specializations for the current user
- `POST /api/specializations` - Add or update a specialization
- `DELETE /api/specializations/<id>` - Delete a specialization

## UI Changes

1. **Settings Page** (`/settings`)
   - New "Kepakaran & Kemahiran" tab added
   - Workers can select categories and add skills for each
   - Maximum 10 skills per category
   - Skills are displayed as tags and can be easily removed

2. **Public Profile Page** (`/profile/<username>`)
   - Specializations section displays before the portfolio
   - Shows all categories the worker specializes in
   - Lists all skills for each category as badges

## Notes

- The `skills` field stores a JSON array of strings
- Each user can only have ONE specialization entry per category (enforced by UNIQUE constraint)
- When a user updates skills for a category they already have, it updates the existing entry
- Maximum 10 skills per category (enforced in the API)
- Maximum 50 characters per skill (enforced in the API)
- Category deletion will cascade and delete associated specializations
- User deletion will cascade and delete their specializations

## Troubleshooting

### Issue: Foreign key constraint failed

**Cause**: You're trying to insert a user_id or category_id that doesn't exist.

**Solution**: Make sure the user and category exist before creating a specialization.

### Issue: UNIQUE constraint failed

**Cause**: You're trying to create a second specialization for the same user and category.

**Solution**: Use the POST endpoint which handles both insert and update automatically.

### Issue: Skills not displaying properly

**Cause**: The skills field might not be valid JSON.

**Solution**: Ensure the skills field contains a valid JSON array:
```sql
-- Check if skills are valid JSON
SELECT id, user_id, skills
FROM worker_specialization
WHERE json_valid(skills) = 0;
```

## Support

If you encounter any issues with the migration, please:
1. Check the application logs
2. Verify the database schema matches the expected structure
3. Ensure all foreign key relationships are intact
4. Contact the development team with error details

---

**Migration Date**: 2026-01-13
**Feature**: Worker Specializations
**Developer**: Claude AI
**Status**: Ready for deployment
