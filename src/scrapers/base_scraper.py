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

    # Class-level variables to cache proxies and skip direct timeout waits once blocked
    _cached_proxies = None
    _use_proxy_directly = False

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

        # Default age limit for notices (in days). Defaults to 180 (6 months). Set to None to disable.
        self.age_limit_days = self.config.get("age_limit_days", 180)

    def _get_indian_proxies(self) -> List[str]:
        """
        Fetch a list of active Indian HTTP proxies from ProxyScrape public API.
        Caches results on the class level to minimize external network requests.
        """
        if BaseScraper._cached_proxies is not None:
            return BaseScraper._cached_proxies
            
        BaseScraper._cached_proxies = []
        try:
            self.logger.info("Fetching fresh free Indian HTTP proxies list...")
            url = "https://api.proxyscrape.com/v4/free-proxy-list/get?request=display_proxies&country=in&protocol=http&proxy_format=protocolipport&format=text"
            # Using direct request with short timeout to avoid hangs
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                proxies = [line.strip() for line in response.text.strip().split("\n") if line.strip()]
                BaseScraper._cached_proxies = proxies
                self.logger.info(f"Retrieved {len(proxies)} Indian proxies from ProxyScrape.")
            else:
                self.logger.warning(f"Failed to fetch proxy list: HTTP {response.status_code}")
        except Exception as e:
            self.logger.warning(f"Error fetching Indian proxy list: {e}")
            
        return BaseScraper._cached_proxies

    @retry(
        stop=stop_after_attempt(settings.MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((requests.RequestException, ConnectionError, TimeoutError)),
        reraise=True
    )
    def fetch_url(self, url: str, params: Optional[Dict[str, Any]] = None) -> requests.Response:
        """
        Fetch a URL with polite rate limiting, request headers, and exponential backoff retry.
        If direct requests are blocked or fail, falls back to rotating Indian HTTP proxies.
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
        
        # If we already flagged direct connection as blocked, immediately route through proxies
        if BaseScraper._use_proxy_directly:
            proxies_list = self._get_indian_proxies()
            if proxies_list:
                shuffled_proxies = list(proxies_list)
                random.shuffle(shuffled_proxies)
                max_proxy_attempts = min(5, len(shuffled_proxies))
                for idx, proxy in enumerate(shuffled_proxies[:max_proxy_attempts]):
                    proxy_dict = {
                        "http": proxy,
                        "https": proxy
                    }
                    self.logger.info(f"Direct request bypassed. Attempting request via proxy ({idx + 1}/{max_proxy_attempts}): {proxy}")
                    try:
                        response = requests.get(
                            url,
                            headers=self.headers,
                            params=params,
                            proxies=proxy_dict,
                            timeout=15,  # Limit proxy timeout to avoid long hangs
                            verify=False
                        )
                        response.raise_for_status()
                        self.logger.info(f"Successfully fetched URL via proxy: {url}")
                        return response
                    except Exception as proxy_err:
                        self.logger.debug(f"Proxy request failed via {proxy}: {proxy_err}")
                self.logger.warning("All direct-proxy bypass attempts failed. Trying direct connection as last resort.")

        # Try direct connection
        try:
            response = requests.get(
                url,
                headers=self.headers,
                params=params,
                timeout=self.timeout,
                verify=False  # Disable SSL verification since some official Govt servers have broken cert paths
            )
            response.raise_for_status()
            return response
        except (requests.RequestException, ConnectionError, TimeoutError) as e:
            self.logger.warning(f"Direct connection failed for {url}: {e}. Enabling proxy-bypass flag for future requests.")
            
            # Direct connection timed out/failed. Mark proxy directly flag to avoid waiting for direct timeouts again.
            BaseScraper._use_proxy_directly = True
            
            # Fetch proxy list for fallback
            proxies_list = self._get_indian_proxies()
            if not proxies_list:
                self.logger.error("No fallback proxies available. Re-raising original exception.")
                raise
                
            shuffled_proxies = list(proxies_list)
            random.shuffle(shuffled_proxies)
            max_proxy_attempts = min(5, len(shuffled_proxies))
            
            for idx, proxy in enumerate(shuffled_proxies[:max_proxy_attempts]):
                proxy_dict = {
                    "http": proxy,
                    "https": proxy
                }
                self.logger.info(f"Attempting fallback request via proxy ({idx + 1}/{max_proxy_attempts}): {proxy}")
                try:
                    response = requests.get(
                        url,
                        headers=self.headers,
                        params=params,
                        proxies=proxy_dict,
                        timeout=15,
                        verify=False
                    )
                    response.raise_for_status()
                    self.logger.info(f"Successfully fetched URL via proxy: {url}")
                    return response
                except Exception as proxy_err:
                    self.logger.debug(f"Proxy request failed via {proxy}: {proxy_err}")
                    
            self.logger.error(f"All {max_proxy_attempts} proxy attempts failed for {url}.")
            raise

    def is_stale(self, date_val: Any) -> bool:
        """
        Check if a given date is older than the configured age limit.
        """
        if not self.age_limit_days or not date_val:
            return False
            
        from utils.normalizer import normalize_date
        from datetime import datetime, timezone
        
        dt = normalize_date(date_val)
        if not dt:
            return False
            
        now = datetime.now(timezone.utc)
        age_days = (now - dt).days
        return age_days > self.age_limit_days

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
                    # Skip if the item is stale based on its posted_at date
                    posted_at = raw.get("posted_at")
                    if posted_at and self.is_stale(posted_at):
                        self.logger.debug(f"Skipping stale notice '{raw.get('title', 'Unknown')}' during validation")
                        continue

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

