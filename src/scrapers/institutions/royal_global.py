import re
from datetime import datetime, timezone
from typing import List, Dict, Any
from bs4 import BeautifulSoup

from scrapers.base_scraper import BaseScraper
from utils.parser_utils import resolve_url
from utils.normalizer import clean_title, normalize_date, normalize_category

class RoyalGlobalScraper(BaseScraper):
    SOURCE_NAME = "Royal Global University"
    SOURCE_TYPE = "university"
    BASE_URL = "https://rgu.ac"
    CATEGORY = "academic"
    SUPPORTED_CONTENT = ["notice", "admission", "exam", "result"]
    RELIABILITY_SCORE = 10

    def __init__(self):
        super().__init__(
            name="royal_global",
            institution="Royal Global University",
            source="Royal Global",
            institution_slug="royal-global-university"
        )
        self.notice_url = "https://rgu.ac/media-corner"

    def scrape(self) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        seen = set()

        try:
            self.logger.info(f"Scraping Royal Global University media/news corner: {self.notice_url}")
            response = self.fetch_url(self.notice_url)
            soup = BeautifulSoup(response.text, "html.parser")

            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                # Skip external links and navigation links
                if href.startswith(("http", "mailto", "javascript", "#")) and "rgu.ac" not in href:
                    continue

                raw_text = a.get_text(strip=True)
                title = clean_title(raw_text)
                resolved_url = resolve_url(self.BASE_URL, href)

                # Skip short generic links
                if not title or title.lower() in ["read more", "view all", "click here", "home", "about", "contact"]:
                    # Try to generate title from the slug itself
                    # e.g., /rgu-launches-uni-news-agency-service-first-time-in-the-north-east-done-by-a-university
                    slug_match = re.search(r"/([a-z0-9\-]{20,80})$", href)
                    if slug_match:
                        slug = slug_match.group(1)
                        title = clean_title(slug.replace("-", " ").capitalize())
                    else:
                        continue

                # Exclude static university navigation elements
                if any(x in title.lower() for x in ["leadership", "vision", "mission", "career", "placement", "facilities", "admission open"]):
                    continue

                if len(title) < 12 or title in seen:
                    continue

                seen.add(title)

                posted_at = None
                date_match = re.search(r"(\d{4})", resolved_url)
                if date_match:
                    try:
                        posted_at = datetime(int(date_match.group(1)), 1, 1, tzinfo=timezone.utc)
                    except ValueError:
                        pass

                if not posted_at:
                    posted_at = datetime.now(timezone.utc)

                category = normalize_category(title)
                attachment_url = resolved_url if resolved_url.lower().endswith(".pdf") else None

                items.append({
                    "title": title,
                    "description": f"News update from Royal Global University (RGU), Guwahati: '{title}'.",
                    "source_url": resolved_url,
                    "canonical_url": resolved_url,
                    "attachment_url": attachment_url,
                    "category": category,
                    "content_type": category,
                    "posted_at": posted_at,
                    "tags": ["Royal Global University", "RGU", "Guwahati", category],
                    "metadata": {
                        "original_page": self.notice_url
                    },
                    "raw_html": str(a)
                })

                if len(items) >= 20:
                    break

        except Exception as e:
            self.logger.error(f"Error scraping Royal Global University: {e}")

        return items
