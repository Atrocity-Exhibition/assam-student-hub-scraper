-- Apply after 001_allow_duplicate_content_hashes.sql to secure public access and update search.
ALTER TABLE notices ADD COLUMN IF NOT EXISTS search_vector_simple tsvector;
CREATE INDEX IF NOT EXISTS idx_notices_search_vector_simple ON notices USING GIN(search_vector_simple);

-- Function to update the search_vector on insert/update
CREATE OR REPLACE FUNCTION notices_search_vector_update()
RETURNS trigger AS $$
BEGIN
  NEW.search_vector :=
    setweight(to_tsvector('english', coalesce(NEW.title, '')), 'A') ||
    setweight(to_tsvector('english', coalesce(NEW.institution, '')), 'B') ||
    setweight(to_tsvector('english', coalesce(NEW.category, '')), 'C') ||
    setweight(to_tsvector('english', coalesce(NEW.description, '') || ' ' || coalesce(NEW.source, '')), 'D');
  NEW.search_vector_simple :=
    setweight(to_tsvector('simple', coalesce(NEW.title, '')), 'A') ||
    setweight(to_tsvector('simple', coalesce(NEW.institution, '')), 'B') ||
    setweight(to_tsvector('simple', coalesce(NEW.category, '')), 'C') ||
    setweight(to_tsvector('simple', coalesce(NEW.description, '') || ' ' || coalesce(NEW.source, '')), 'D');
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS notices_search_vector_trigger ON notices;
CREATE TRIGGER notices_search_vector_trigger
  BEFORE INSERT OR UPDATE ON notices
  FOR EACH ROW EXECUTE FUNCTION notices_search_vector_update();

UPDATE notices SET search_vector = search_vector WHERE search_vector_simple IS NULL;

-- Ranked Full-Text Search RPC Function
DROP FUNCTION IF EXISTS search_notices(TEXT, TEXT, INTEGER, INTEGER);
CREATE OR REPLACE FUNCTION search_notices(
  search_query  TEXT,
  p_category    TEXT    DEFAULT NULL,
  p_page        INT     DEFAULT 1,
  p_page_size   INT     DEFAULT 12,
  p_institution_slug TEXT DEFAULT NULL,
  p_institution_id BIGINT DEFAULT NULL,
  p_is_official BOOLEAN DEFAULT NULL,
  p_date_after TIMESTAMPTZ DEFAULT NULL,
  p_experience TEXT DEFAULT NULL,
  p_salary TEXT DEFAULT NULL,
  p_education TEXT DEFAULT NULL,
  p_academic_only BOOLEAN DEFAULT FALSE,
  p_exclude_academic BOOLEAN DEFAULT FALSE,
  p_exclude_id BIGINT DEFAULT NULL
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
  scraper_name          TEXT,
  search_rank           FLOAT4,
  total_count           BIGINT
) AS $$
DECLARE
  ts_query tsquery;
  simple_query tsquery;
  offset_val INT;
BEGIN
  ts_query := plainto_tsquery('english', search_query);
  simple_query := plainto_tsquery('simple', search_query);
  p_page := GREATEST(COALESCE(p_page, 1), 1);
  p_page_size := LEAST(GREATEST(COALESCE(p_page_size, 12), 1), 100);
  offset_val := (p_page - 1) * p_page_size;

  RETURN QUERY
  WITH matched AS (
    SELECT n.id, n.title, n.slug, n.description, n.category, n.content_type,
      n.institution, n.institution_slug, n.source, n.source_url, n.posted_at,
      n.scraped_at, n.created_at, n.updated_at::TEXT AS updated_at, n.tags,
      n.attachment_url, n.institution_id, n.is_active, n.is_official,
      n.merged_into_notice_id, n.scraper_name,
      (GREATEST(ts_rank_cd(n.search_vector, ts_query),
                ts_rank_cd(n.search_vector_simple, simple_query)) *
       (1.0 / (1.0 + EXTRACT(EPOCH FROM (now() - coalesce(n.posted_at, n.created_at))) / 86400.0 / 30.0)))::FLOAT4 AS search_rank,
      count(*) OVER() AS total_count
    FROM notices n
    WHERE n.is_active = true
      AND n.merged_into_notice_id IS NULL
      AND (n.search_vector @@ ts_query OR n.search_vector_simple @@ simple_query)
      AND (p_category IS NULL OR lower(n.category) = lower(p_category))
      AND (p_institution_slug IS NULL OR n.institution_slug = p_institution_slug)
      AND (p_institution_id IS NULL OR n.institution_id = p_institution_id)
      AND (p_is_official IS NULL OR n.is_official = p_is_official)
      AND (p_date_after IS NULL OR n.posted_at >= p_date_after)
      AND (p_experience IS NULL OR n.metadata->>'experience_level' = p_experience)
      AND (p_salary IS NULL OR n.metadata->>'salary_range' = p_salary)
      AND (p_education IS NULL OR n.metadata->>'education_level' = p_education)
      AND (p_exclude_id IS NULL OR n.id <> p_exclude_id)
      AND (NOT p_academic_only OR (
        lower(n.category) <> 'recruitment' AND coalesce(n.institution_slug, '') NOT IN (
          'assam-public-service-commission', 'state-level-police-recruitment-board',
          'gauhati-high-court', 'all-job-assam', 'numaligarh-refinery-limited',
          'assamjobnews', 'daily-assam-job', 'assam-career', 'ncs-portal', 'aesrb',
          'nhm-assam', 'seba', 'ahsec'
        )
      ))
      AND (NOT p_exclude_academic OR coalesce(n.institution_slug, '') NOT IN (
        'gauhati-university', 'cotton-university', 'dibrugarh-university',
        'tezpur-university', 'bodoland-university', 'mangaldai-college',
        'assam-university', 'astu', 'krishna-kanta-handiqui-state-open-university',
        'assam-womens-university'
      ))
  )
  SELECT matched.id, matched.title, matched.slug, matched.description,
    matched.category, matched.content_type, matched.institution,
    matched.institution_slug, matched.source, matched.source_url,
    matched.posted_at, matched.scraped_at, matched.created_at,
    matched.updated_at, matched.tags, matched.attachment_url,
    matched.institution_id, matched.is_active, matched.is_official,
    matched.merged_into_notice_id, matched.scraper_name, matched.search_rank,
    matched.total_count
  FROM matched
  ORDER BY matched.search_rank DESC, matched.posted_at DESC NULLS LAST
  LIMIT p_page_size OFFSET offset_val;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = public, extensions, pg_temp;

-- Fuzzy Search RPC Function
DROP FUNCTION IF EXISTS fuzzy_search_notices(TEXT, TEXT, FLOAT, INTEGER);
CREATE OR REPLACE FUNCTION fuzzy_search_notices(
  search_query  TEXT,
  p_category    TEXT    DEFAULT NULL,
  p_threshold   FLOAT   DEFAULT 0.25,
  p_page_size   INT     DEFAULT 12,
  p_page        INT     DEFAULT 1,
  p_institution_slug TEXT DEFAULT NULL,
  p_institution_id BIGINT DEFAULT NULL,
  p_is_official BOOLEAN DEFAULT NULL,
  p_date_after TIMESTAMPTZ DEFAULT NULL,
  p_experience TEXT DEFAULT NULL,
  p_salary TEXT DEFAULT NULL,
  p_education TEXT DEFAULT NULL,
  p_academic_only BOOLEAN DEFAULT FALSE,
  p_exclude_academic BOOLEAN DEFAULT FALSE,
  p_exclude_id BIGINT DEFAULT NULL
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
  scraper_name          TEXT,
  search_rank           FLOAT4,
  total_count           BIGINT
) AS $$
DECLARE
  offset_val INT;
BEGIN
  p_page := GREATEST(COALESCE(p_page, 1), 1);
  p_page_size := LEAST(GREATEST(COALESCE(p_page_size, 12), 1), 100);
  offset_val := (p_page - 1) * p_page_size;
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
    n.scraper_name,
    word_similarity(search_query, n.title)::FLOAT4 AS search_rank,
    count(*) OVER() AS total_count
  FROM notices n
  WHERE
    n.is_active = true
    AND n.merged_into_notice_id IS NULL
    AND word_similarity(search_query, n.title) > p_threshold
    AND (p_category IS NULL OR lower(n.category) = lower(p_category))
    AND (p_institution_slug IS NULL OR n.institution_slug = p_institution_slug)
    AND (p_institution_id IS NULL OR n.institution_id = p_institution_id)
    AND (p_is_official IS NULL OR n.is_official = p_is_official)
    AND (p_date_after IS NULL OR n.posted_at >= p_date_after)
    AND (p_experience IS NULL OR n.metadata->>'experience_level' = p_experience)
    AND (p_salary IS NULL OR n.metadata->>'salary_range' = p_salary)
    AND (p_education IS NULL OR n.metadata->>'education_level' = p_education)
    AND (p_exclude_id IS NULL OR n.id <> p_exclude_id)
    AND (NOT p_academic_only OR (
      lower(n.category) <> 'recruitment' AND coalesce(n.institution_slug, '') NOT IN (
        'assam-public-service-commission', 'state-level-police-recruitment-board',
        'gauhati-high-court', 'all-job-assam', 'numaligarh-refinery-limited',
        'assamjobnews', 'daily-assam-job', 'assam-career', 'ncs-portal', 'aesrb',
        'nhm-assam', 'seba', 'ahsec'
      )
    ))
    AND (NOT p_exclude_academic OR coalesce(n.institution_slug, '') NOT IN (
      'gauhati-university', 'cotton-university', 'dibrugarh-university',
      'tezpur-university', 'bodoland-university', 'mangaldai-college',
      'assam-university', 'astu', 'krishna-kanta-handiqui-state-open-university',
      'assam-womens-university'
    ))
  ORDER BY search_rank DESC, n.posted_at DESC NULLS LAST
  LIMIT p_page_size OFFSET offset_val;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = public, extensions, pg_temp;

-- ============================================================
-- ROW LEVEL SECURITY AND POLICIES
-- ============================================================

ALTER TABLE institutions ENABLE ROW LEVEL SECURITY;
ALTER TABLE notices ENABLE ROW LEVEL SECURITY;
ALTER TABLE scraper_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE saved_notices ENABLE ROW LEVEL SECURITY;
ALTER TABLE search_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE saved_searches ENABLE ROW LEVEL SECURITY;

-- Reset policies on these tables so no older permissive policy can widen access.
DO $$
DECLARE
  existing_policy RECORD;
BEGIN
  FOR existing_policy IN
    SELECT schemaname, tablename, policyname
    FROM pg_policies
    WHERE schemaname = 'public'
      AND tablename = ANY (ARRAY['institutions', 'notices', 'scraper_runs', 'saved_notices', 'search_logs', 'saved_searches'])
  LOOP
    EXECUTE format('DROP POLICY %I ON %I.%I', existing_policy.policyname, existing_policy.schemaname, existing_policy.tablename);
  END LOOP;
END;
$$;

DROP POLICY IF EXISTS "Public can read institutions" ON institutions;
CREATE POLICY "Public can read institutions" ON institutions FOR SELECT TO anon, authenticated USING (true);
DROP POLICY IF EXISTS "Public can read active notices" ON notices;
CREATE POLICY "Public can read active notices" ON notices FOR SELECT TO anon, authenticated
  USING (is_active = true AND merged_into_notice_id IS NULL);
DROP POLICY IF EXISTS "Public can read scraper status" ON scraper_runs;
CREATE POLICY "Public can read scraper status" ON scraper_runs FOR SELECT TO anon, authenticated USING (true);
DROP POLICY IF EXISTS "Owners manage saved notices" ON saved_notices;
CREATE POLICY "Owners manage saved notices" ON saved_notices FOR ALL TO authenticated
  USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());
DROP POLICY IF EXISTS "Users insert search logs" ON search_logs;
CREATE POLICY "Users insert search logs" ON search_logs FOR INSERT TO anon, authenticated
  WITH CHECK (user_id IS NULL OR user_id = auth.uid());
DROP POLICY IF EXISTS "Users read own logs" ON search_logs;
DROP POLICY IF EXISTS "Allow insert for all" ON search_logs;

DROP POLICY IF EXISTS "Users manage own saved searches" ON saved_searches;
CREATE POLICY "Users manage own saved searches" ON saved_searches
  TO authenticated
  USING (user_id = auth.uid())
  WITH CHECK (user_id = auth.uid());

REVOKE ALL ON TABLE institutions, notices, scraper_runs, saved_notices, search_logs, saved_searches FROM PUBLIC, anon, authenticated;
GRANT SELECT ON TABLE institutions TO anon, authenticated;
GRANT SELECT (id, title, description, source, source_url, category, content_type,
  institution, institution_slug, posted_at, last_seen_at, is_active, tags, slug,
  scraped_at, created_at, updated_at, attachment_url, institution_id, is_official,
  merged_into_notice_id, scraper_name, metadata)
  ON TABLE notices TO anon, authenticated;
GRANT SELECT (id, scraper_name, status, started_at, completed_at, items_scraped,
  items_inserted, items_updated, duration_seconds, created_at)
  ON TABLE scraper_runs TO anon, authenticated;
GRANT SELECT, INSERT, DELETE ON TABLE saved_notices TO authenticated;
GRANT INSERT (query, results_count, search_type, search_duration_ms, category, user_id)
  ON TABLE search_logs TO anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE saved_searches TO authenticated;

CREATE OR REPLACE FUNCTION get_trending_searches(p_limit INT DEFAULT 8)
RETURNS TABLE(query TEXT)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, extensions, pg_temp AS $$
  SELECT lower(trim(sl.query)) AS query
  FROM public.search_logs AS sl
  WHERE sl.created_at >= now() - interval '7 days'
    AND sl.results_count > 0
    AND length(trim(sl.query)) >= 2
  GROUP BY lower(trim(sl.query))
  HAVING count(*) >= 2
  ORDER BY count(*) DESC, lower(trim(sl.query))
  LIMIT LEAST(GREATEST(COALESCE(p_limit, 8), 1), 20);
$$;
REVOKE ALL ON FUNCTION get_trending_searches(INT) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION get_trending_searches(INT) TO anon, authenticated;
REVOKE ALL ON FUNCTION search_notices(TEXT, TEXT, INT, INT, TEXT, BIGINT, BOOLEAN, TIMESTAMPTZ, TEXT, TEXT, TEXT, BOOLEAN, BOOLEAN, BIGINT) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION search_notices(TEXT, TEXT, INT, INT, TEXT, BIGINT, BOOLEAN, TIMESTAMPTZ, TEXT, TEXT, TEXT, BOOLEAN, BOOLEAN, BIGINT) TO anon, authenticated;
REVOKE ALL ON FUNCTION fuzzy_search_notices(TEXT, TEXT, FLOAT, INT, INT, TEXT, BIGINT, BOOLEAN, TIMESTAMPTZ, TEXT, TEXT, TEXT, BOOLEAN, BOOLEAN, BIGINT) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION fuzzy_search_notices(TEXT, TEXT, FLOAT, INT, INT, TEXT, BIGINT, BOOLEAN, TIMESTAMPTZ, TEXT, TEXT, TEXT, BOOLEAN, BOOLEAN, BIGINT) TO anon, authenticated;

