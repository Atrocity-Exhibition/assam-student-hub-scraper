import re
from datetime import datetime, timezone
from typing import List, Dict, Any
from bs4 import BeautifulSoup

from scrapers.base_scraper import BaseScraper
from utils.parser_utils import resolve_url
from utils.normalizer import clean_title, normalize_date, normalize_category

class AssamUniversityScraper(BaseScraper):
    SOURCE_NAME = "Assam University, Silchar"
    SOURCE_TYPE = "university"
    BASE_URL = "http://www.aus.ac.in"
    CATEGORY = "mixed"
    SUPPORTED_CONTENT = ["recruitment", "result", "exam", "admission", "scholarship", "notice"]
    RELIABILITY_SCORE = 10

    def __init__(self):
        super().__init__(
            name="assam_university",
            institution="Assam University, Silchar",
            source="Assam University"
        )
        self.target_url = "http://www.aus.ac.in"
        self.relevant_keywords = [
            "notice", "circular", "advertisement", "recruitment", "vacancy", 
            "admission", "exam", "result", "routine", "schedule", "tender", 
            "corrigendum", "interview", "shortlisted"
        ]

    def scrape(self) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        seen = set()

        try:
            self.logger.info(f"Scraping Assam University Silchar homepage: {self.target_url}")
            response = self.fetch_url(self.target_url)
            soup = BeautifulSoup(response.text, "html.parser")

            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                title = clean_title(a.get_text(strip=True))
                search_text = title.lower()

                # Basic validity checks
                if len(title) < 10 or title in seen:
                    continue

                # Relevance check for notices
                is_relevant = any(k in search_text for k in self.relevant_keywords) or "wp-content/uploads" in href
                if not is_relevant:
                    continue

                seen.add(title)

                resolved_url = resolve_url(self.target_url, href)

                # Date extraction logic: try to parse YYYY/MM from upload paths
                posted_at = None
                date_match = re.search(r"wp-content/uploads/(\d{4})/(\d{2})/", resolved_url)
                if date_match:
                    year = int(date_match.group(1))
                    month = int(date_match.group(2))
                    try:
                        # Default to the first day of that month as posting date
                        posted_at = datetime(year, month, 1, tzinfo=timezone.utc)
                    except ValueError:
                        posted_at = datetime.now(timezone.utc)
                else:
                    # Fallback: check if text has dates like DD-MM-YYYY
                    text_date = re.search(r"(\d{2}[-/\.]\d{2}[-/\.]\d{4})", title)
                    if text_date:
                        posted_at = normalize_date(text_date.group(1))

                # If no date resolved, default to current time
                if not posted_at:
                    posted_at = datetime.now(timezone.utc)

                # Determine category
                category = normalize_category(title)

                attachment_url = None
                if resolved_url.lower().endswith(".pdf"):
                    attachment_url = resolved_url

                items.append({
                    "title": title,
                    "description": f"Official notice from Assam University, Silchar: '{title}'.",
                    "source_url": resolved_url,
                    "canonical_url": resolved_url,
                    "attachment_url": attachment_url,
                    "category": category,
                    "content_type": category,
                    "posted_at": posted_at,
                    "tags": ["Assam University", "AUS", "Silchar", category],
                    "metadata": {
                        "original_page": self.target_url,
                    },
                    "raw_html": str(a)
                })

                if len(items) >= 40:
                    break

        except Exception as e:
            self.logger.error(f"Error scraping {self.target_url}: {e}")

        return items
