-- SQLite Migration for Gig Reference Photos Feature
-- Execute these queries in your SQLite database

-- 1. Create GigPhoto table for client reference photos
CREATE TABLE IF NOT EXISTS gig_photo (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    gig_id INTEGER NOT NULL,
    uploader_id INTEGER NOT NULL,
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size INTEGER,
    caption TEXT,
    photo_type VARCHAR(50) DEFAULT 'reference',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (gig_id) REFERENCES gig(id),
    FOREIGN KEY (uploader_id) REFERENCES user(id)
);

-- 2. Add indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_gig_photo_gig_id ON gig_photo(gig_id);
CREATE INDEX IF NOT EXISTS idx_gig_photo_uploader_id ON gig_photo(uploader_id);
CREATE INDEX IF NOT EXISTS idx_gig_photo_created_at ON gig_photo(created_at ASC);

-- Notes:
-- - photo_type values: 'reference', 'example', 'inspiration'
-- - Gig photos are uploaded by clients when posting/editing gigs
-- - These are different from work_photo which are uploaded during work execution
