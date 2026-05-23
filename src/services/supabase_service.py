import logging
from typing import List, Dict, Any
from supabase import create_client

from config.settings import (
    SUPABASE_URL,
    SUPABASE_KEY,
)
from models.item import ScrapedItem

logger = logging.getLogger("services.supabase")

# Initialize the Supabase Client
supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY,
)

_institutions_cache: Dict[str, int] = {}

def get_institutions_cache(force_refresh: bool = False) -> Dict[str, int]:
    """
    Lazy-loaded cache mapping institution slugs to their database IDs.
    """
    global _institutions_cache
    if not _institutions_cache or force_refresh:
        try:
            logger.info("Fetching institutions mapping from database...")
            response = supabase.table("institutions").select("id, slug").execute()
            if response.data:
                _institutions_cache = {row["slug"]: row["id"] for row in response.data}
                logger.info(f"Cached {len(_institutions_cache)} institutions: {_institutions_cache}")
            else:
                logger.warning("No institutions found in database to cache.")
        except Exception as e:
            logger.error(f"Failed to fetch institutions cache: {e}")
    return _institutions_cache

def bulk_upsert_notices(items: List[ScrapedItem]) -> Dict[str, Any]:
    """
    Ingest a list of scraped items into the Supabase 'notices' table.
    Ensures deduplication on the database side using the unique 'source_url' field.
    Prioritizes official sources and sets up redirect graphs for duplicate items.
    
    :param items: List of validated ScrapedItem objects
    :return: A status dictionary containing success boolean, record count, and errors if any
    """
    if not items:
        logger.info("Database Ingestion: No items to insert.")
        return {
            "success": True, 
            "count": 0, 
            "inserted_count": 0, 
            "updated_count": 0
        }

    # Resolve institution IDs using the cache
    inst_cache = get_institutions_cache()
    for item in items:
        if item.institution_slug and item.institution_slug in inst_cache:
            item.institution_id = inst_cache[item.institution_slug]
        else:
            logger.warning(f"Could not resolve institution_id for slug: '{item.institution_slug}'")

    # Deduplicate items by source_url in-memory to prevent Postgres ON CONFLICT DO UPDATE errors
    seen_urls = set()
    unique_items = []
    for item in items:
        if item.source_url not in seen_urls:
            seen_urls.add(item.source_url)
            unique_items.append(item)
        else:
            logger.warning(f"In-memory deduplication: skipping duplicate source_url: {item.source_url}")

    # Determine which ones already exist in the database (updates) and which ones are new (inserts)
    inserted_count = 0
    updated_count = 0
    try:
        urls = list(seen_urls)
        existing_urls = set()
        for i in range(0, len(urls), 100):
            batch_urls = urls[i:i+100]
            response_existing = supabase.table("notices").select("source_url").in_("source_url", batch_urls).execute()
            if response_existing.data:
                for row in response_existing.data:
                    existing_urls.add(row["source_url"])
        
        for url in seen_urls:
            if url in existing_urls:
                updated_count += 1
            else:
                inserted_count += 1
    except Exception as e:
        logger.error(f"Error querying existing source_urls for stats computation: {e}")

    # Duplicate merging logic using content_hash and reliability_score
    aggregator_updates_needed = []
    try:
        hashes = [item.content_hash for item in unique_items if item.content_hash]
        existing_by_hash = {}
        if hashes:
            for i in range(0, len(hashes), 100):
                batch_hashes = hashes[i:i+100]
                resp = supabase.table("notices").select("id, content_hash, source_url, reliability_score").in_("content_hash", batch_hashes).execute()
                if resp.data:
                    for row in resp.data:
                        if row["content_hash"] not in existing_by_hash:
                            existing_by_hash[row["content_hash"]] = []
                        existing_by_hash[row["content_hash"]].append(row)
        
        for item in unique_items:
            if item.content_hash and item.content_hash in existing_by_hash:
                existing_records = existing_by_hash[item.content_hash]
                # Filter out the record if it matches our own source_url (to avoid comparing with ourselves on update)
                other_existing = [r for r in existing_records if r["source_url"] != item.source_url]
                if other_existing:
                    best_existing = max(other_existing, key=lambda x: x.get("reliability_score") or 10)
                    best_rel = best_existing.get("reliability_score") or 10
                    
                    if item.reliability_score < best_rel:
                        # Case A: Incoming notice is less reliable than the existing one -> merge incoming into existing
                        item.merged_into_notice_id = best_existing["id"]
                        logger.info(f"Deduplication: Merging notice '{item.title}' (reliability {item.reliability_score}) into existing more reliable notice ID {best_existing['id']} (reliability {best_rel})")
                    else:
                        # Case B: Incoming notice is more or equally reliable -> merge existing into incoming (after incoming is inserted)
                        aggregator_updates_needed.append((best_existing["id"], item.content_hash))
    except Exception as e:
        logger.error(f"Error resolving duplicate notices merging: {e}")

    # Convert Pydantic models to dicts formatted for PG database columns
    records = [item.to_dict() for item in unique_items]
    logger.info(f"Database Ingestion: Preparing bulk upsert for {len(records)} notices")

    try:
        # Perform bulk upsert using PostgREST upsert interface.
        # Delineates duplicate conflicts on the unique index of 'source_url'.
        response = supabase.table("notices").upsert(
            records,
            on_conflict="source_url"
        ).execute()

        # Extract number of rows touched (inserted/updated)
        affected_count = len(response.data) if response.data else len(records)
        logger.info(f"Database Ingestion: Successfully upserted {affected_count} records. (New inserts: {inserted_count}, Updates: {updated_count})")
        
        # Post-upsert: Link less reliable existing notices to the newly inserted more reliable notices (Case B)
        if aggregator_updates_needed and response.data:
            hash_to_inserted = {}
            for row in response.data:
                if row.get("content_hash"):
                    # Map to (id, reliability_score)
                    rel = row.get("reliability_score") or 10
                    if row["content_hash"] not in hash_to_inserted or rel > hash_to_inserted[row["content_hash"]][1]:
                        hash_to_inserted[row["content_hash"]] = (row["id"], rel)
            
            for agg_id, content_hash in aggregator_updates_needed:
                if content_hash in hash_to_inserted:
                    official_id, official_rel = hash_to_inserted[content_hash]
                    try:
                        # Double-check that we aren't linking a record to itself or to something less reliable
                        supabase.table("notices").update({"merged_into_notice_id": official_id}).eq("id", agg_id).execute()
                        logger.info(f"Deduplication: Linked lower reliability notice ID {agg_id} to new higher reliability notice ID {official_id}")
                    except Exception as err:
                        logger.error(f"Failed to link aggregator notice {agg_id} to official notice {official_id}: {err}")

        return {
            "success": True, 
            "count": affected_count, 
            "inserted_count": inserted_count,
            "updated_count": updated_count,
            "data": response.data
        }
    except Exception as e:
        logger.error(f"Database Ingestion Error: Bulk upsert failed. Details: {e}")
        return {
            "success": False, 
            "error": str(e), 
            "count": 0,
            "inserted_count": 0,
            "updated_count": 0
        }

