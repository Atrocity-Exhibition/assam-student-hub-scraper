import argparse
import sys
import logging

from scrapers.apsc import APSCScraper
from scrapers.slprb import SLPRBScraper
from scrapers.gauhati import GauhatiScraper
from scrapers.cotton import CottonScraper
from scrapers.dibrugarh import DibrugarhScraper
from scrapers.assam_career import AssamCareerScraper
from scrapers.daily_assam_job import DailyAssamJobScraper
from scrapers.nhm_assam import NHMAssamScraper
from scrapers.aesrb import AESRBScraper
from scrapers.ncs_portal import NCSPortalScraper
from scrapers.tezpur import TezpurScraper
from scrapers.bodoland import BodolandScraper
from scrapers.mangaldai import MangaldaiScraper
from scrapers.ahsec import AHSECScraper
from scrapers.seba import SEBAScraper
from services.supabase_service import bulk_upsert_notices

def main():
    # Setup Argument Parser
    parser = argparse.ArgumentParser(description="AssamStudentHub Aggregator - Backend Scrapers CLI")
    
    parser.add_argument(
        "--scraper", "-s",
        choices=[
            "apsc", "slprb", "gauhati", "cotton", "dibrugarh",
            "assam_career", "daily_assam_job", "nhm_assam", "aesrb", "ncs_portal",
            "tezpur", "bodoland", "mangaldai", "ahsec", "seba"
        ],
        default="apsc",
        help="Scraper to execute (default: apsc)"
    )
    parser.add_argument(
        "--year", "-y",
        type=int,
        default=None,
        help="Target year to scrape notices from (default: current year)"
    )
    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=None,
        help="Limit the number of records processed"
    )
    parser.add_argument(
        "--dry-run", "-d",
        action="store_true",
        help="Scrape and validate, but do NOT execute Supabase database ingestion"
    )

    args = parser.parse_args()
    
    logger = logging.getLogger("Runner")
    logger.info("Initializing AssamStudentHub Aggregator CLI runner")

    # Scraper selection block
    if args.scraper == "apsc":
        scraper = APSCScraper(year=args.year)
    elif args.scraper == "slprb":
        scraper = SLPRBScraper()
    elif args.scraper == "gauhati":
        scraper = GauhatiScraper()
    elif args.scraper == "cotton":
        scraper = CottonScraper(limit=args.limit)
    elif args.scraper == "dibrugarh":
        scraper = DibrugarhScraper(limit=args.limit or 30)
    elif args.scraper == "assam_career":
        scraper = AssamCareerScraper()
    elif args.scraper == "daily_assam_job":
        scraper = DailyAssamJobScraper()
    elif args.scraper == "nhm_assam":
        scraper = NHMAssamScraper()
    elif args.scraper == "aesrb":
        scraper = AESRBScraper()
    elif args.scraper == "ncs_portal":
        scraper = NCSPortalScraper()
    elif args.scraper == "tezpur":
        scraper = TezpurScraper()
    elif args.scraper == "bodoland":
        scraper = BodolandScraper()
    elif args.scraper == "mangaldai":
        scraper = MangaldaiScraper()
    elif args.scraper == "ahsec":
        scraper = AHSECScraper()
    elif args.scraper == "seba":
        scraper = SEBAScraper()
    else:
        logger.error(f"Requested scraper '{args.scraper}' is not supported yet.")
        sys.exit(1)

    # Execute the scraping process
    if args.dry_run:
        validated_items = scraper.run()
        if args.limit:
            logger.info(f"Applying limit: restricting records to first {args.limit}")
            validated_items = validated_items[:args.limit]

        if not validated_items:
            logger.info("No items were retrieved or validated. Exiting.")
            sys.exit(0)

        logger.info(f"DRY RUN: Displaying {len(validated_items)} validated records")
        for idx, item in enumerate(validated_items):
            print(f"\n--- Item [{idx + 1}] ---")
            print(f"Title:            {item.title}")
            print(f"Institution:      {item.institution} ({item.institution_slug})")
            print(f"Category / Type:  {item.category} / {item.content_type}")
            print(f"Posted At:        {item.posted_at}")
            print(f"Source URL:       {item.source_url}")
            print(f"Attachment URL:   {item.attachment_url}")
            print(f"Generated Slug:   {item.slug}")
            print(f"Content Hash:     {item.content_hash}")
            print(f"Tags:             {item.tags}")
            print(f"Snapshot Length:  {len(item.raw_html) if item.raw_html else 0} chars")
    else:
        from services.monitor_service import ScraperRunTracker
        
        logger.info(f"Ingestion Mode: Running scraper '{args.scraper}' with tracking")
        with ScraperRunTracker(args.scraper) as tracker:
            validated_items = scraper.run()
            if args.limit:
                logger.info(f"Applying limit: restricting records to first {args.limit}")
                validated_items = validated_items[:args.limit]

            if not validated_items:
                logger.info("No items were retrieved or validated.")
                tracker.set_counts(0, 0, 0)
                sys.exit(0)

            logger.info("Ingestion Mode: Upserting records into Supabase")
            result = bulk_upsert_notices(validated_items)
            
            if result["success"]:
                logger.info(f"Ingestion complete: processed {result['count']} items successfully.")
                tracker.set_counts(
                    scraped=len(validated_items),
                    inserted=result.get("inserted_count", 0),
                    updated=result.get("updated_count", 0)
                )
            else:
                logger.error(f"Ingestion failed. Database Error: {result.get('error')}")
                tracker.add_error(result.get("error", "Unknown database error"))
                sys.exit(1)

if __name__ == "__main__":
    main()
