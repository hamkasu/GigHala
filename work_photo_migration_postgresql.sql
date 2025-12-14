-- PostgreSQL Migration for Work Photo Feature
-- Execute these queries in your PostgreSQL database

-- 1. Create WorkPhoto table
CREATE TABLE work_photo (
    id SERIAL PRIMARY KEY,
    gig_id INTEGER NOT NULL,
    uploader_id INTEGER NOT NULL,
    uploader_type VARCHAR(20) NOT NULL,
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size INTEGER,
    caption TEXT,
    upload_stage VARCHAR(50) DEFAULT 'work_in_progress',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (gig_id) REFERENCES gig(id),
    FOREIGN KEY (uploader_id) REFERENCES "user"(id)
);

-- 2. Add indexes for better query performance
CREATE INDEX idx_work_photo_gig_id ON work_photo(gig_id);
CREATE INDEX idx_work_photo_uploader_id ON work_photo(uploader_id);
CREATE INDEX idx_work_photo_created_at ON work_photo(created_at DESC);

-- 3. Update Application table
ALTER TABLE application ADD COLUMN work_submitted BOOLEAN DEFAULT FALSE;
ALTER TABLE application ADD COLUMN work_submission_date TIMESTAMP;

-- 4. Verify the changes
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'work_photo';

SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'application'
AND column_name IN ('work_submitted', 'work_submission_date');
