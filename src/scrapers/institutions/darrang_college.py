import re
from datetime import datetime, timezone
from typing import List, Dict, Any
from bs4 import BeautifulSoup

from scrapers.base_scraper import BaseScraper
from utils.parser_utils import resolve_url
from utils.normalizer import clean_title, normalize_date, normalize_category

class DarrangCollegeScraper(BaseScraper):
    SOURCE_NAME = "Darrang College"
    SOURCE_TYPE = "university"
    BASE_URL = "https://darrangcollege.ac.in"
    CATEGORY = "academic"
    SUPPORTED_CONTENT = ["notice", "admission", "exam", "result"]
    RELIABILITY_SCORE = 10

    def __init__(self):
        super().__init__(
            name="darrang_college",
            institution="Darrang College",
            source="Darrang College",
            institution_slug="darrang-college"
        )
        self.notice_url = "https://darrangcollege.ac.in/headnotice.php"

    def scrape(self) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        seen = set()

        try:
            self.logger.info(f"Scraping Darrang College notice board: {self.notice_url}")
            response = self.fetch_url(self.notice_url)
            soup = BeautifulSoup(response.text, "html.parser")

            # Look for links pointing to notice uploads or pdfs
            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                title = clean_title(a.get_text(strip=True))

                # Check if it's a notice link (has upload path or pdf or a general notice tag)
                if not any(x in href.lower() for x in ["upload/", ".pdf", "headnotice.php"]) and len(title) < 15:
                    continue

                if "headnotice.php" in href and len(title) < 10:
                    # Skip generic "View" links
                    continue

                if len(title) < 8 or title in seen:
                    continue

                seen.add(title)
                resolved_url = resolve_url(self.BASE_URL, href)

                # Determine dates from text or use fallback
                posted_at = None
                date_match = re.search(r"(\d{2}[-/\.]\d{2}[-/\.]\d{4})", title)
                if date_match:
                    posted_at = normalize_date(date_match.group(1))
                
                # Check for upload timestamp in filename, e.g. upload/headnotice/1776508295.pdf
                if not posted_at:
                    ts_match = re.search(r"upload/headnotice/(\d{9,10})", resolved_url)
                    if ts_match:
                        try:
                            posted_at = datetime.fromtimestamp(int(ts_match.group(1)), tz=timezone.utc)
                        except (ValueError, OverflowError):
                            pass

                if not posted_at:
                    posted_at = datetime.now(timezone.utc)

                category = normalize_category(title)
                attachment_url = resolved_url if resolved_url.lower().endswith(".pdf") else None

                items.append({
                    "title": title,
                    "description": f"Notice from Darrang College notice board: '{title}'. Check the official college portal for details.",
                    "source_url": resolved_url,
                    "canonical_url": resolved_url,
                    "attachment_url": attachment_url,
                    "category": category,
                    "content_type": category,
                    "posted_at": posted_at,
                    "tags": ["Darrang College", "Tezpur", "Sonitpur", category],
                    "metadata": {
                        "original_page": self.notice_url
                    },
                    "raw_html": str(a)
                })

                if len(items) >= 20:
                    break

        except Exception as e:
            self.logger.error(f"Error scraping Darrang College notices: {e}")

        return items
