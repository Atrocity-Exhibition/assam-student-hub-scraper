-- Multiple source URLs may legitimately contain identical notice content.
-- Keep the lookup index, but remove the old one-row-per-hash constraint.
ALTER TABLE notices DROP CONSTRAINT IF EXISTS notices_content_hash_key;
