import argparse
import sys
import logging

from config.scrapers_config import SCRAPER_CONFIG
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

# New Scrapers implemented in Phase 1
from scrapers.assam_university import AssamUniversityScraper
from scrapers.astu import ASTUScraper
from scrapers.ghc import GHCScraper
from scrapers.all_job_assam import AllJobAssamScraper

# Batch 2 Scrapers
from scrapers.kkhsou import KKHSOUScraper
from scrapers.awu import AWUScraper
from scrapers.nrl import NRLScraper
from scrapers.assam_job_news import AssamJobNewsScraper

from services.supabase_service import bulk_upsert_notices

# Register scraper classes mapping to SCRAPER_CONFIG keys
SCRAPER_CLASSES = {
    "apsc": APSCScraper,
    "slprb": SLPRBScraper,
    "gauhati": GauhatiScraper,
    "cotton": CottonScraper,
    "dibrugarh": DibrugarhScraper,
    "assam_career": AssamCareerScraper,
    "daily_assam_job": DailyAssamJobScraper,
    "nhm_assam": NHMAssamScraper,
    "aesrb": AESRBScraper,
    "ncs_portal": NCSPortalScraper,
    "tezpur": TezpurScraper,
    "bodoland": BodolandScraper,
    "mangaldai": MangaldaiScraper,
    "ahsec": AHSECScraper,
    "seba": SEBAScraper,
    
    # New Scrapers
    "assam_university": AssamUniversityScraper,
    "astu": ASTUScraper,
    "ghc": GHCScraper,
    "all_job_assam": AllJobAssamScraper,
    
    # Batch 2 Scrapers
    "kkhsou": KKHSOUScraper,
    "awu": AWUScraper,
    "nrl": NRLScraper,
    "assam_job_news": AssamJobNewsScraper
}

def main():
    # Setup Argument Parser
    parser = argparse.ArgumentParser(description="AssamStudentHub Aggregator - Dynamic Backend Scrapers CLI")
    
    # Core Scraper Executions
    parser.add_argument(
        "--scraper", "-s",
        choices=list(SCRAPER_CONFIG.keys()),
        default=None,
        help="Scraper to execute (default: run APSC if no filters specified)"
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Execute all scrapers in sequence"
    )
    
    # Metadata-driven scheduling filters
    parser.add_argument(
        "--frequency", "-f",
        choices=["6h", "12h", "24h"],
        default=None,
        help="Execute all scrapers matching this scheduling frequency"
    )
    parser.add_argument(
        "--priority", "-p",
        choices=["high", "medium", "low"],
        default=None,
        help="Execute all scrapers matching this priority"
    )
    parser.add_argument(
        "--category", "-c",
        choices=["jobs", "academic", "mixed"],
        default=None,
        help="Execute all scrapers matching this category"
    )

    # General modifiers
    parser.add_argument(
        "--year", "-y",
        type=int,
        default=None,
        help="Target year to scrape notices from (only supported on select scrapers like APSC)"
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

    # Resolve list of scrapers to run
    scrapers_to_run = []
    if args.all:
        scrapers_to_run = list(SCRAPER_CONFIG.keys())
    elif args.scraper:
        scrapers_to_run.append(args.scraper)
    elif args.frequency or args.priority or args.category:
        for name, cfg in SCRAPER_CONFIG.items():
            match = True
            if args.frequency and cfg.get("frequency") != args.frequency:
                match = False
            if args.priority and cfg.get("priority") != args.priority:
                match = False
            if args.category and cfg.get("category") != args.category:
                match = False
            if match:
                scrapers_to_run.append(name)
    else:
        # Backward compatibility default fallback
        scrapers_to_run.append("apsc")

    if not scrapers_to_run:
        logger.warning("No scrapers matched the specified scheduler filters. Exiting.")
        sys.exit(0)

    logger.info(f"Target scrapers scheduled for execution: {scrapers_to_run}")

    # Process all selected scrapers sequentially (future-proof layout for task queue workers)
    for name in scrapers_to_run:
        logger.info(f"\n==================================================")
        logger.info(f"Starting Scraper Execution: {name}")
        logger.info(f"==================================================")
        
        cls = SCRAPER_CLASSES[name]
        
        # Instantiate scraper object with appropriate arguments
        if name == "apsc":
            scraper = cls(year=args.year)
        elif name == "cotton":
            scraper = cls(limit=args.limit or 15)
        elif name == "dibrugarh":
            scraper = cls(limit=args.limit or 30)
        else:
            scraper = cls()

        if args.dry_run:
            validated_items = scraper.run()
            if args.limit and name not in ("cotton", "dibrugarh"):
                logger.info(f"Applying limit: restricting records to first {args.limit}")
                validated_items = validated_items[:args.limit]

            if not validated_items:
                logger.info(f"No items were retrieved or validated for '{name}'.")
                continue

            logger.info(f"DRY RUN: Displaying {len(validated_items)} validated records for '{name}':")
            for idx, item in enumerate(validated_items):
                print(f"\n--- Item [{idx + 1}] from '{name}' ---")
                print(f"Title:            {item.title}")
                print(f"Institution:      {item.institution} ({item.institution_slug})")
                print(f"Category / Type:  {item.category} / {item.content_type}")
                print(f"Posted At:        {item.posted_at}")
                print(f"Source URL:       {item.source_url}")
                print(f"Canonical URL:    {item.canonical_url}")
                print(f"Attachment URL:   {item.attachment_url}")
                print(f"Generated Slug:   {item.slug}")
                print(f"Content Hash:     {item.content_hash}")
                print(f"Reliability:      {item.reliability_score}")
                print(f"Tags:             {item.tags}")
        else:
            from services.monitor_service import ScraperRunTracker
            
            logger.info(f"Ingestion Mode: Running scraper '{name}' with run tracker")
            with ScraperRunTracker(name) as tracker:
                validated_items = scraper.run()
                if args.limit and name not in ("cotton", "dibrugarh"):
                    logger.info(f"Applying limit: restricting records to first {args.limit}")
                    validated_items = validated_items[:args.limit]

                if not validated_items:
                    logger.info(f"No items were retrieved or validated for '{name}'.")
                    tracker.set_counts(0, 0, 0)
                    continue

                logger.info(f"Ingestion Mode: Bulk upserting {len(validated_items)} records for '{name}' into Supabase")
                result = bulk_upsert_notices(validated_items)
                
                if result["success"]:
                    logger.info(f"Ingestion complete for '{name}': processed {result['count']} items successfully.")
                    tracker.set_counts(
                        scraped=len(validated_items),
                        inserted=result.get("inserted_count", 0),
                        updated=result.get("updated_count", 0)
                    )
                else:
                    logger.error(f"Ingestion failed for '{name}'. Database Error: {result.get('error')}")
                    tracker.add_error(result.get("error", "Unknown database error"))

if __name__ == "__main__":
    main()
