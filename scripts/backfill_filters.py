import os
import sys
import logging
from dotenv import load_dotenv
from supabase import create_client

# Setup Logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("FilterBackfiller")

# Resolve paths
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(script_dir, "..", "src"))
dotenv_path = os.path.join(script_dir, "..", ".env")
load_dotenv(dotenv_path)

from utils.normalizer import classify_filter_metadata

# Init Supabase
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

if not supabase_url or not supabase_key:
    logger.error("SUPABASE_URL or SUPABASE_KEY not found in environment. Exiting.")
    sys.exit(1)

supabase = create_client(supabase_url, supabase_key)

def backfill():
    logger.info("Fetching recruitment notices to backfill...")
    
    # Fetch active recruitment notices
    res = supabase.table("notices").select("id, title, description, metadata").eq("category", "recruitment").execute()
    notices = res.data
    
    if not notices:
        logger.info("No notices found to backfill.")
        return
        
    total = len(notices)
    logger.info(f"Found {total} notices. Starting backfill...")
    
    success_count = 0
    for idx, notice in enumerate(notices, start=1):
        notice_id = notice["id"]
        title = notice.get("title") or ""
        description = notice.get("description") or ""
        metadata = notice.get("metadata") or {}
        
        updated_metadata = classify_filter_metadata(title, description, metadata)
        
        try:
            supabase.table("notices").update({"metadata": updated_metadata}).eq("id", notice_id).execute()
            success_count += 1
            if idx % 50 == 0 or idx == total:
                logger.info(f"Processed {idx}/{total} notices...")
        except Exception as e:
            logger.error(f"Failed to update notice {notice_id}: {e}")
            
    logger.info(f"Backfill complete. Successfully updated {success_count}/{total} notices.")

if __name__ == "__main__":
    backfill()
