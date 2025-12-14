-- Category Migration SQL Queries
-- Execute these queries to update existing gig categories to the new schema

-- 1. First, check current category distribution
SELECT category, COUNT(*) as count
FROM gig
GROUP BY category
ORDER BY count DESC;

-- 2. Update existing categories to new IDs (where IDs have changed)

-- Update 'video' to 'photography' (Video Editing -> Fotografi, Videografi & Animasi)
UPDATE gig
SET category = 'photography'
WHERE category = 'video';

-- Update 'tech' to 'web' (Tech & Programming -> Pembangunan Web)
UPDATE gig
SET category = 'web'
WHERE category = 'tech';

-- Update 'voice' to 'creative_other' (Voice Over -> Lain-lain Kreatif)
UPDATE gig
SET category = 'creative_other'
WHERE category = 'voice';

-- Update 'data' to 'micro_tasks' (Data Entry -> Micro-Tasks & Tugasan)
UPDATE gig
SET category = 'micro_tasks'
WHERE category = 'data';

-- 3. Categories that keep the same ID (no update needed, just name changes):
-- - 'design' (stays as 'design')
-- - 'writing' (stays as 'writing')
-- - 'tutoring' (stays as 'tutoring')
-- - 'marketing' (stays as 'marketing')
-- - 'admin' (stays as 'admin')
-- - 'content' (stays as 'content')

-- 4. New categories available for future gigs:
-- - 'general' (Kerja Am)
-- - 'delivery' (Penghantaran & Logistik)
-- - 'events' (Pengurusan Acara)
-- - 'caregiving' (Penjagaan & Perkhidmatan)

-- 5. Verify the updates
SELECT category, COUNT(*) as count
FROM gig
GROUP BY category
ORDER BY count DESC;

-- 6. Check for any invalid categories (should return 0 rows)
SELECT id, title, category
FROM gig
WHERE category NOT IN (
    'design', 'writing', 'content', 'photography', 'web',
    'marketing', 'tutoring', 'admin', 'general', 'delivery',
    'micro_tasks', 'events', 'caregiving', 'creative_other'
);

-- Summary of Changes:
-- Old Category ID -> New Category ID (New Display Name)
-- ================================================================
-- design          -> design          (Design & Kreatif)
-- writing         -> writing         (Penulisan & Terjemahan)
-- content         -> content         (Penciptaan Kandungan)
-- video           -> photography     (Fotografi, Videografi & Animasi)
-- web             -> web             (Pembangunan Web)
-- marketing       -> marketing       (Pemasaran Digital)
-- tutoring        -> tutoring        (Tunjuk Ajar)
-- admin           -> admin           (Sokongan Admin & Pentadbiran Maya)
-- general         -> general         (Kerja Am) [NEW]
-- delivery        -> delivery        (Penghantaran & Logistik) [NEW]
-- micro_tasks     -> micro_tasks     (Micro-Tasks & Tugasan)
-- events          -> events          (Pengurusan Acara) [NEW]
-- caregiving      -> caregiving      (Penjagaan & Perkhidmatan) [NEW]
-- creative_other  -> creative_other  (Lain-lain Kreatif)
--
-- Removed/Merged:
-- tech            -> web             (merged into Pembangunan Web)
-- voice           -> creative_other  (merged into Lain-lain Kreatif)
-- data            -> micro_tasks     (merged into Micro-Tasks & Tugasan)
