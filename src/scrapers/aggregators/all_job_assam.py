import re
from datetime import datetime, timezone
from typing import List, Dict, Any
from bs4 import BeautifulSoup

from scrapers.base_scraper import BaseScraper
from utils.parser_utils import resolve_url
from utils.normalizer import clean_title, normalize_date, normalize_category

class AllJobAssamScraper(BaseScraper):
    SOURCE_NAME = "AllJobAssam"
    SOURCE_TYPE = "aggregator"
    BASE_URL = "https://alljobassam.com"
    CATEGORY = "jobs"
    SUPPORTED_CONTENT = ["recruitment", "result", "exam"]
    RELIABILITY_SCORE = 6

    def __init__(self):
        super().__init__(
            name="all_job_assam",
            institution="AllJobAssam",
            source="AllJobAssam.com",
            institution_slug="all-job-assam"
        )
        self.target_url = "https://alljobassam.com"

    def scrape(self) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        seen = set()

        try:
            self.logger.info(f"Scraping AllJobAssam homepage: {self.target_url}")
            response = self.fetch_url(self.target_url)
            soup = BeautifulSoup(response.text, "html.parser")

            # AllJobAssam uses GeneratePress blocks; articles have class gb-headline-text inside h2 elements
            headlines = soup.find_all("h2", class_="gb-headline-text")
            self.logger.info(f"Found {len(headlines)} headlines on AllJobAssam")

            for h2 in headlines:
                a = h2.find("a")
                if not a:
                    continue

                title = clean_title(a.get_text(strip=True))
                href = a["href"].strip()

                # Ignore general headings like "Latest Post" or short items
                if len(title) < 15 or "latest post" in title.lower() or title in seen:
                    continue

                seen.add(title)

                resolved_url = resolve_url(self.BASE_URL, href)

                # Traverse parent to find the time tag containing publication date
                posted_at = None
                parent = h2.find_parent("div", class_="gb-container")
                if parent:
                    time_el = parent.find("time", class_="entry-date")
                    if time_el and time_el.get("datetime"):
                        posted_at = normalize_date(time_el["datetime"])

                if not posted_at:
                    posted_at = datetime.now(timezone.utc)

                # Excerpt / default description
                description = f"Job listing: '{title}'. Sourced from AllJobAssam aggregator board."

                # Categorize based on title
                category = normalize_category(title)
                if category == "notice":
                    category = "recruitment"  # Aggregators are job-focused

                items.append({
                    "title": title,
                    "description": description,
                    "source_url": resolved_url,
                    "canonical_url": resolved_url,
                    "attachment_url": None, # Aggregators link to application posts, not raw PDFs
                    "category": category,
                    "content_type": category,
                    "posted_at": posted_at,
                    "tags": ["AllJobAssam", "Job", "Aggregator", category],
                    "metadata": {
                        "original_page": self.target_url,
                    },
                    "raw_html": str(h2)
                })

                if len(items) >= 40:
                    break

        except Exception as e:
            self.logger.error(f"Error scraping AllJobAssam page: {e}")

        return items
