-- ============================================================
-- Phase 8 Schema Update: Data Platform Enhancements & Seeding
-- Execute this script in your Supabase SQL Editor.
-- ============================================================

-- 1. Upgrade notices table with canonical and soft-delete support
ALTER TABLE notices 
  ADD COLUMN IF NOT EXISTS canonical_url TEXT,
  ADD COLUMN IF NOT EXISTS removed_at TIMESTAMP WITH TIME ZONE,
  ADD COLUMN IF NOT EXISTS reliability_score INTEGER DEFAULT 10;

-- Create index on reliability_score for ranking queries
CREATE INDEX IF NOT EXISTS idx_notices_reliability_score ON notices(reliability_score);

-- 2. Upgrade scraper_runs table with detailed failure analytics
ALTER TABLE scraper_runs
  ADD COLUMN IF NOT EXISTS duration_seconds INTEGER,
  ADD COLUMN IF NOT EXISTS traceback TEXT;

-- 3. Seed new institutions for Phase 1 scrapers
INSERT INTO institutions (name, slug, description, website, location)
VALUES
    (
        'Assam University, Silchar', 
        'assam-university', 
        'A Central University established in Silchar, Assam in 1994, offering academic programs across multiple fields in Southern Assam.', 
        'https://www.aus.ac.in', 
        'Silchar, Cachar, Assam'
    ),
    (
        'Assam Science and Technology University', 
        'astu', 
        'A State University established by the Government of Assam to regulate and provide higher education in engineering and technology disciplines.', 
        'https://astu.ac.in', 
        'Jalukbari, Guwahati, Assam'
    ),
    (
        'Gauhati High Court', 
        'gauhati-high-court', 
        'The principal judicial court for the state of Assam, Nagaland, Mizoram, and Arunachal Pradesh, responsible for judicial recruitments.', 
        'https://ghconline.gov.in', 
        'Guwahati, Assam'
    ),
    (
        'AllJobAssam', 
        'all-job-assam', 
        'Aggregated local job board listing public and private sector vacancies across Assam districts.', 
        'https://alljobassam.com', 
        'Assam, India'
    )
ON CONFLICT (slug) DO UPDATE
SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    website = EXCLUDED.website,
    location = EXCLUDED.location;
