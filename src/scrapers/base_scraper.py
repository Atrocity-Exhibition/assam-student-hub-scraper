import os
import time
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import requests
import urllib3
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from models.item import ScrapedItem
from config import settings

# Disable warnings from insecure SSL connections (required for some official Govt servers)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Ensure log directory exists
os.makedirs("logs", exist_ok=True)

# Configure logging to write to both stdout and a log file
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/scraper.log", encoding="utf-8")
    ]
)

logger = logging.getLogger("BaseScraper")

class BaseScraper(ABC):
    # Mandatory metadata contracts to be defined in subclasses
    SOURCE_NAME: str = ""
    SOURCE_TYPE: str = ""      # "government" | "university" | "aggregator" | "other"
    BASE_URL: str = ""
    CATEGORY: str = ""         # "jobs" | "academic" | "mixed"
    SUPPORTED_CONTENT: List[str] = []
    RELIABILITY_SCORE: int = 10

    def __init__(self, name: str, institution: str, source: Optional[str] = None, institution_slug: Optional[str] = None):
        """
        Initialize the base scraper.
        :param name: Scraper identifier (e.g. 'apsc')
        :param institution: Target organization name (e.g. 'Assam Public Service Commission')
        :param source: Optional human-readable source name (e.g. 'APSC')
        :param institution_slug: Optional slug override to match the database institutions table
        """
        self.name = name
        self.institution = institution
        self.source = source or name.upper()
        self.institution_slug = institution_slug
        self.logger = logging.getLogger(f"scraper.{name}")
        self.headers = settings.DEFAULT_HEADERS.copy()

        # Load metadata-driven scheduling config & rate limit preferences
        from config.scrapers_config import SCRAPER_CONFIG
        self.config = SCRAPER_CONFIG.get(name, {})
        
        rate_limit = self.config.get("rate_limit", {})
        self.delay_seconds = float(rate_limit.get("delay_seconds", settings.REQUEST_DELAY))
        self.jitter = bool(rate_limit.get("jitter", True))
        
        # Override default request timeout if specified in config
        self.timeout = int(self.config.get("timeout", settings.REQUEST_TIMEOUT))

    @retry(
        stop=stop_after_attempt(settings.MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((requests.RequestException, ConnectionError, TimeoutError)),
        reraise=True
    )
    def fetch_url(self, url: str, params: Optional[Dict[str, Any]] = None) -> requests.Response:
        """
        Fetch a URL with polite rate limiting, request headers, and exponential backoff retry.
        """
        self.logger.info(f"Fetching URL: {url}")
        
        # Polite crawl delay with optional jitter
        import random
        if self.jitter:
            actual_delay = random.uniform(self.delay_seconds * 0.5, self.delay_seconds * 1.5)
        else:
            actual_delay = self.delay_seconds
            
        self.logger.debug(f"Sleeping for {actual_delay:.2f} seconds before request")
        time.sleep(actual_delay)
        
        response = requests.get(
            url,
            headers=self.headers,
            params=params,
            timeout=self.timeout,
            verify=False  # Disable SSL verification since some official portals have broken cert paths
        )
        response.raise_for_status()
        return response

    @abstractmethod
    def scrape(self) -> List[Dict[str, Any]]:
        """
        Abstract method to parse target sites.
        Must return a list of raw dictionaries containing item data.
        """
        pass

    def run(self) -> List[ScrapedItem]:
        """
        Wrapper to run the scraper, parse records, and validate them against ScrapedItem model.
        Returns a list of validated ScrapedItem objects.
        """
        self.logger.info(f"Starting execution of scraper '{self.name}'")
        validated_items: List[ScrapedItem] = []
        
        try:
            raw_items = self.scrape()
            self.logger.info(f"Retrieved {len(raw_items)} raw records from source")
            
            for idx, raw in enumerate(raw_items):
                try:
                    # Inject base parameters if missing
                    raw["institution"] = self.institution
                    if self.institution_slug:
                        raw["institution_slug"] = self.institution_slug
                    raw["scraper_name"] = self.name
                    raw["source"] = self.source
                    raw["reliability_score"] = getattr(self, "RELIABILITY_SCORE", 10)
                    
                    item = ScrapedItem(**raw)
                    validated_items.append(item)
                except Exception as ve:
                    self.logger.error(
                        f"Item validation failed at row index {idx} in {self.name}: "
                        f"Title: '{raw.get('title', 'Unknown')}', Error: {ve}"
                    )
            
            self.logger.info(
                f"Successfully parsed and validated {len(validated_items)} out of {len(raw_items)} items"
            )
        except Exception as e:
            self.logger.exception(f"Scraper execution crashed: {e}")
            
        return validated_items

