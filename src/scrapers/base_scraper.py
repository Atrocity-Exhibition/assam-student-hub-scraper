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
    def __init__(self, name: str, institution: str, source: Optional[str] = None):
        """
        Initialize the base scraper.
        :param name: Scraper identifier (e.g. 'apsc')
        :param institution: Target organization name (e.g. 'Assam Public Service Commission')
        :param source: Optional human-readable source name (e.g. 'APSC')
        """
        self.name = name
        self.institution = institution
        self.source = source or name.upper()
        self.logger = logging.getLogger(f"scraper.{name}")
        self.headers = settings.DEFAULT_HEADERS.copy()

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
        
        # Polite crawl delay
        time.sleep(settings.REQUEST_DELAY)
        
        response = requests.get(
            url,
            headers=self.headers,
            params=params,
            timeout=settings.REQUEST_TIMEOUT,
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
                    raw["scraper_name"] = self.name
                    raw["source"] = self.source
                    
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
