-- ============================================================
-- Phase 7 RPC Fix v3: Drop old functions first, then recreate
-- Run this ENTIRE script in your Supabase SQL Editor.
-- ============================================================

-- Step 1: Drop existing functions
DROP FUNCTION IF EXISTS search_notices(TEXT, TEXT, INTEGER, INTEGER);
DROP FUNCTION IF EXISTS fuzzy_search_notices(TEXT, TEXT, FLOAT, INTEGER);

-- Step 2: Recreate with correct INT8 column types
CREATE OR REPLACE FUNCTION search_notices(
  search_query  TEXT,
  p_category    TEXT    DEFAULT NULL,
  p_page        INT     DEFAULT 1,
  p_page_size   INT     DEFAULT 6
)
RETURNS TABLE (
  id                    INT8,
  title                 TEXT,
  slug                  TEXT,
  description           TEXT,
  category              TEXT,
  content_type          TEXT,
  institution           TEXT,
  institution_slug      TEXT,
  source                TEXT,
  source_url            TEXT,
  posted_at             TIMESTAMPTZ,
  scraped_at            TIMESTAMPTZ,
  created_at            TIMESTAMPTZ,
  updated_at            TEXT,
  tags                  TEXT[],
  attachment_url        TEXT,
  institution_id        INT8,
  is_active             BOOLEAN,
  is_official           BOOLEAN,
  merged_into_notice_id INT8,
  content_hash          TEXT,
  scraper_name          TEXT,
  search_rank           FLOAT4
) AS $$
DECLARE
  ts_query   tsquery;
  offset_val INT := (p_page - 1) * p_page_size;
BEGIN
  ts_query := plainto_tsquery('english', search_query);

  RETURN QUERY
  SELECT
    n.id,
    n.title,
    n.slug,
    n.description,
    n.category,
    n.content_type,
    n.institution,
    n.institution_slug,
    n.source,
    n.source_url,
    n.posted_at,
    n.scraped_at,
    n.created_at,
    n.updated_at::TEXT,
    n.tags,
    n.attachment_url,
    n.institution_id,
    n.is_active,
    n.is_official,
    n.merged_into_notice_id,
    n.content_hash,
    n.scraper_name,
    (
      ts_rank_cd(n.search_vector, ts_query) *
      (1.0 / (1.0 + EXTRACT(EPOCH FROM (now() - coalesce(n.posted_at, n.created_at))) / 86400.0 / 30.0))
    )::FLOAT4 AS search_rank
  FROM notices n
  WHERE
    n.is_active = true
    AND n.merged_into_notice_id IS NULL
    AND n.search_vector @@ ts_query
    AND (p_category IS NULL OR lower(n.category) = lower(p_category))
  ORDER BY search_rank DESC
  LIMIT p_page_size
  OFFSET offset_val;
END;
$$ LANGUAGE plpgsql STABLE;


CREATE OR REPLACE FUNCTION fuzzy_search_notices(
  search_query  TEXT,
  p_category    TEXT    DEFAULT NULL,
  p_threshold   FLOAT   DEFAULT 0.25,
  p_page_size   INT     DEFAULT 6
)
RETURNS TABLE (
  id                    INT8,
  title                 TEXT,
  slug                  TEXT,
  description           TEXT,
  category              TEXT,
  content_type          TEXT,
  institution           TEXT,
  institution_slug      TEXT,
  source                TEXT,
  source_url            TEXT,
  posted_at             TIMESTAMPTZ,
  scraped_at            TIMESTAMPTZ,
  created_at            TIMESTAMPTZ,
  updated_at            TEXT,
  tags                  TEXT[],
  attachment_url        TEXT,
  institution_id        INT8,
  is_active             BOOLEAN,
  is_official           BOOLEAN,
  merged_into_notice_id INT8,
  content_hash          TEXT,
  scraper_name          TEXT,
  search_rank           FLOAT4
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    n.id,
    n.title,
    n.slug,
    n.description,
    n.category,
    n.content_type,
    n.institution,
    n.institution_slug,
    n.source,
    n.source_url,
    n.posted_at,
    n.scraped_at,
    n.created_at,
    n.updated_at::TEXT,
    n.tags,
    n.attachment_url,
    n.institution_id,
    n.is_active,
    n.is_official,
    n.merged_into_notice_id,
    n.content_hash,
    n.scraper_name,
    word_similarity(search_query, n.title)::FLOAT4 AS search_rank
  FROM notices n
  WHERE
    n.is_active = true
    AND n.merged_into_notice_id IS NULL
    AND word_similarity(search_query, n.title) > p_threshold
    AND (p_category IS NULL OR lower(n.category) = lower(p_category))
  ORDER BY search_rank DESC, n.posted_at DESC NULLS LAST
  LIMIT p_page_size;
END;
$$ LANGUAGE plpgsql STABLE;
