-- ============================================================
-- Phase 7 Schema Update: Search & Recommendation Infrastructure
-- Execute this ENTIRE script in your Supabase SQL Editor.
-- ============================================================

-- 1. Enable trigram extension for fuzzy/typo-tolerant search
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ============================================================
-- FULL TEXT SEARCH INFRASTRUCTURE
-- ============================================================

-- 2. Add weighted tsvector column
--    A = title (highest weight — title matches must dominate ranking)
--    B = institution (high weight — very common search intent)
--    C = category (medium weight — browsing by type)
--    D = description + source (lowest — supporting context)
ALTER TABLE notices
  ADD COLUMN IF NOT EXISTS search_vector tsvector;

-- 3. Populate search_vector for ALL existing rows with proper weights
UPDATE notices
SET search_vector =
  setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
  setweight(to_tsvector('english', coalesce(institution, '')), 'B') ||
  setweight(to_tsvector('english', coalesce(category, '')), 'C') ||
  setweight(to_tsvector('english', coalesce(description, '') || ' ' || coalesce(source, '')), 'D');

-- 4. GIN index for fast FTS queries
CREATE INDEX IF NOT EXISTS idx_notices_search_vector
  ON notices USING GIN(search_vector);

-- 5. GIN trigram index on title for fuzzy fallback queries
CREATE INDEX IF NOT EXISTS idx_notices_title_trgm
  ON notices USING GIN(title gin_trgm_ops);

-- 6. Auto-update trigger: regenerate search_vector on INSERT or UPDATE
CREATE OR REPLACE FUNCTION notices_search_vector_update()
RETURNS trigger AS $$
BEGIN
  NEW.search_vector :=
    setweight(to_tsvector('english', coalesce(NEW.title, '')), 'A') ||
    setweight(to_tsvector('english', coalesce(NEW.institution, '')), 'B') ||
    setweight(to_tsvector('english', coalesce(NEW.category, '')), 'C') ||
    setweight(to_tsvector('english', coalesce(NEW.description, '') || ' ' || coalesce(NEW.source, '')), 'D');
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS notices_search_vector_trigger ON notices;
CREATE TRIGGER notices_search_vector_trigger
  BEFORE INSERT OR UPDATE ON notices
  FOR EACH ROW EXECUTE FUNCTION notices_search_vector_update();

-- ============================================================
-- RANKED FTS RPC FUNCTION
-- Callable via: supabase.rpc('search_notices', {...})
-- Rank = ts_rank_cd (cover density) × recency decay factor
-- Recency decay: score halves every 30 days of age
-- ============================================================
CREATE OR REPLACE FUNCTION search_notices(
  search_query  TEXT,
  p_category    TEXT    DEFAULT NULL,
  p_page        INT     DEFAULT 1,
  p_page_size   INT     DEFAULT 6
)
RETURNS TABLE (
  id              BIGINT,
  title           TEXT,
  slug            TEXT,
  description     TEXT,
  category        TEXT,
  content_type    TEXT,
  institution     TEXT,
  institution_slug TEXT,
  source          TEXT,
  source_url      TEXT,
  posted_at       TIMESTAMPTZ,
  scraped_at      TIMESTAMPTZ,
  created_at      TIMESTAMPTZ,
  updated_at      TEXT,
  tags            TEXT[],
  attachment_url  TEXT,
  institution_id  INT,
  is_active       BOOLEAN,
  is_official     BOOLEAN,
  merged_into_notice_id BIGINT,
  content_hash    TEXT,
  scraper_name    TEXT,
  search_rank     FLOAT4
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
    -- Hybrid rank: FTS cover-density rank × exponential recency decay
    -- Decay factor: 1 / (1 + age_in_days / 30), so a 30-day-old notice
    -- has 50% the score boost of a fresh notice at equal text relevance.
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

-- ============================================================
-- FUZZY SEARCH RPC FUNCTION (trigram-based typo fallback)
-- Uses word_similarity() for better multi-word query handling.
-- Called when FTS returns 0 results.
-- ============================================================
CREATE OR REPLACE FUNCTION fuzzy_search_notices(
  search_query  TEXT,
  p_category    TEXT    DEFAULT NULL,
  p_threshold   FLOAT   DEFAULT 0.25,
  p_page_size   INT     DEFAULT 6
)
RETURNS TABLE (
  id              BIGINT,
  title           TEXT,
  slug            TEXT,
  description     TEXT,
  category        TEXT,
  content_type    TEXT,
  institution     TEXT,
  institution_slug TEXT,
  source          TEXT,
  source_url      TEXT,
  posted_at       TIMESTAMPTZ,
  scraped_at      TIMESTAMPTZ,
  created_at      TIMESTAMPTZ,
  updated_at      TEXT,
  tags            TEXT[],
  attachment_url  TEXT,
  institution_id  INT,
  is_active       BOOLEAN,
  is_official     BOOLEAN,
  merged_into_notice_id BIGINT,
  content_hash    TEXT,
  scraper_name    TEXT,
  search_rank     FLOAT4
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

-- ============================================================
-- SEARCH ANALYTICS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS search_logs (
  id               BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  query            TEXT NOT NULL,
  results_count    INTEGER DEFAULT 0 NOT NULL,
  search_type      TEXT DEFAULT 'fts',          -- 'fts' | 'fuzzy' | 'ilike'
  search_duration_ms INTEGER,                   -- query execution time in ms (for perf monitoring)
  category         TEXT,
  user_id          UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  created_at       TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now()) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_search_logs_query      ON search_logs(query);
CREATE INDEX IF NOT EXISTS idx_search_logs_created_at ON search_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_search_logs_user_id    ON search_logs(user_id);

-- ============================================================
-- SAVED SEARCHES TABLE
-- Future-proof schema: notify_enabled for Phase 8 alerts,
-- last_checked_at for incremental notification matching.
-- ============================================================
CREATE TABLE IF NOT EXISTS saved_searches (
  id               BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  user_id          UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  query            TEXT NOT NULL,
  category         TEXT,
  label            TEXT,                        -- user-defined friendly name
  notify_enabled   BOOLEAN DEFAULT false NOT NULL, -- reserved for Phase 8 notifications
  last_checked_at  TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now()) NOT NULL,
  created_at       TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now()) NOT NULL,
  UNIQUE(user_id, query, category)
);

CREATE INDEX IF NOT EXISTS idx_saved_searches_user_id ON saved_searches(user_id);

-- ============================================================
-- ROW LEVEL SECURITY: saved_searches and search_logs
-- ============================================================

-- search_logs: public insert (anon logging), authenticated read-own
ALTER TABLE search_logs ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow insert for all" ON search_logs;
CREATE POLICY "Allow insert for all" ON search_logs FOR INSERT WITH CHECK (true);
DROP POLICY IF EXISTS "Users read own logs" ON search_logs;
CREATE POLICY "Users read own logs" ON search_logs FOR SELECT USING (user_id = auth.uid() OR user_id IS NULL);

-- saved_searches: users manage only their own rows
ALTER TABLE saved_searches ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users manage own saved searches" ON saved_searches;
CREATE POLICY "Users manage own saved searches" ON saved_searches
  USING (user_id = auth.uid())
  WITH CHECK (user_id = auth.uid());
