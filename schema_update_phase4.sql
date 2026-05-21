-- Phase 4 Migration: Adding institution_id foreign key, indexing, and seeding APSC and SLPRB

-- 1. Add institution_id to notices table referencing institutions(id)
ALTER TABLE notices ADD COLUMN IF NOT EXISTS institution_id BIGINT REFERENCES institutions(id) ON DELETE SET NULL;

-- 2. Create index on institution_id
CREATE INDEX IF NOT EXISTS idx_notices_institution_id ON notices(institution_id);

-- 3. Seed APSC and SLPRB into institutions table
INSERT INTO institutions (name, slug, description, website, location)
VALUES 
    ('Assam Public Service Commission', 'assam-public-service-commission', 'The premier recruitment body of the Government of Assam for selecting candidates for state civil services and other administrative posts.', 'https://apsc.nic.in', 'Khanapara, Guwahati, Assam'),
    ('State Level Police Recruitment Board', 'state-level-police-recruitment-board', 'The board responsible for conducting recruitment examinations for various posts in the Assam Police and other allied departments.', 'https://slprbassam.in', 'Guwahati, Assam')
ON CONFLICT (slug) DO UPDATE 
SET 
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    website = EXCLUDED.website,
    location = EXCLUDED.location;

-- 4. Backfill institution_id on existing notices from matching slugs
UPDATE notices
SET institution_id = institutions.id
FROM institutions
WHERE notices.institution_slug = institutions.slug;
