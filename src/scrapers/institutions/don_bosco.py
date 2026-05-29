import re
from datetime import datetime, timezone
from typing import List, Dict, Any
from bs4 import BeautifulSoup

from scrapers.base_scraper import BaseScraper
from utils.parser_utils import resolve_url
from utils.normalizer import clean_title, normalize_date, normalize_category

class DonBoscoScraper(BaseScraper):
    SOURCE_NAME = "Assam Don Bosco University"
    SOURCE_TYPE = "university"
    BASE_URL = "https://dbuniversity.ac.in"
    CATEGORY = "academic"
    SUPPORTED_CONTENT = ["notice", "admission", "exam", "result"]
    RELIABILITY_SCORE = 10

    def __init__(self):
        super().__init__(
            name="don_bosco",
            institution="Assam Don Bosco University",
            source="Don Bosco",
            institution_slug="don-bosco-university"
        )
        self.notice_url = "https://dbuniversity.ac.in/announcement.php"

    def scrape(self) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        seen = set()

        try:
            self.logger.info(f"Scraping Don Bosco University announcements: {self.notice_url}")
            response = self.fetch_url(self.notice_url)
            soup = BeautifulSoup(response.text, "html.parser")

            # Look for all PDF files or links in the main table/lists
            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                title = clean_title(a.get_text(strip=True))

                # Look for files ending with .pdf, or in a Regulations_Syllabi folder, or in pdfs/
                is_valid = any(x in href.lower() for x in [".pdf", "pdfs/", "regulations_syllabi", "news_events"])
                if not is_valid:
                    continue

                # Filter out general navigation links
                if any(x in title.lower() for x in ["our patron", "why don bosco", "philosophy", "governance", "history", "exchange"]):
                    continue

                if len(title) < 10 or title in seen:
                    continue

                seen.add(title)
                resolved_url = resolve_url(self.BASE_URL, href)

                posted_at = None
                # Check for year patterns like 2025-26
                year_match = re.search(r"(\d{4})", title)
                if year_match:
                    try:
                        posted_at = datetime(int(year_match.group(1)), 1, 1, tzinfo=timezone.utc)
                    except ValueError:
                        pass

                if not posted_at:
                    posted_at = datetime.now(timezone.utc)

                category = normalize_category(title)
                attachment_url = resolved_url if resolved_url.lower().endswith(".pdf") else None

                items.append({
                    "title": title,
                    "description": f"Official academic notice / guidelines from Assam Don Bosco University (ADBU): '{title}'.",
                    "source_url": resolved_url,
                    "canonical_url": resolved_url,
                    "attachment_url": attachment_url,
                    "category": category,
                    "content_type": category,
                    "posted_at": posted_at,
                    "tags": ["Don Bosco University", "ADBU", "Guwahati", category],
                    "metadata": {
                        "original_page": self.notice_url
                    },
                    "raw_html": str(a)
                })

                if len(items) >= 20:
                    break

        except Exception as e:
            self.logger.error(f"Error scraping Don Bosco: {e}")

        return items
