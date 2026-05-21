-- Database Schema Update - Phase 6: Prioritization & Deduplication Redirects
-- Execute this script in your Supabase SQL Editor.

-- 1. Add is_official column to track high-trust official sources vs aggregators
ALTER TABLE notices ADD COLUMN IF NOT EXISTS is_official BOOLEAN DEFAULT true NOT NULL;

-- 2. Add merged_into_notice_id self-referencing foreign key for soft-duplicate redirects
ALTER TABLE notices ADD COLUMN IF NOT EXISTS merged_into_notice_id BIGINT REFERENCES notices(id) ON DELETE SET NULL;

-- 3. Update existing records to mark aggregators as unofficial
UPDATE notices 
SET is_official = false 
WHERE scraper_name IN ('assam_career', 'daily_assam_job', 'ncs_portal');

-- 4. Create indices for prioritized search and redirect graph traversals
CREATE INDEX IF NOT EXISTS idx_notices_is_official ON notices(is_official);
CREATE INDEX IF NOT EXISTS idx_notices_merged_into_notice_id ON notices(merged_into_notice_id);
