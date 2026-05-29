import re
from datetime import datetime, timezone
from typing import List, Dict, Any
from bs4 import BeautifulSoup

from scrapers.base_scraper import BaseScraper
from utils.parser_utils import resolve_url, parse_date
from utils.normalizer import clean_title, normalize_category

class PanduCollegeScraper(BaseScraper):
    SOURCE_NAME = "Pandu College"
    SOURCE_TYPE = "university"
    BASE_URL = "https://panducollege.ac.in"
    CATEGORY = "academic"
    SUPPORTED_CONTENT = ["notice", "admission", "exam", "result"]
    RELIABILITY_SCORE = 10

    def __init__(self):
        super().__init__(
            name="pandu_college",
            institution="Pandu College",
            source="Pandu College",
            institution_slug="pandu-college"
        )
        self.notice_url = "https://panducollege.ac.in/notice.php"

    def scrape(self) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        seen = set()

        try:
            self.logger.info(f"Scraping Pandu College notice table: {self.notice_url}")
            response = self.fetch_url(self.notice_url)
            soup = BeautifulSoup(response.text, "html.parser")

            table = soup.find("table")
            if not table:
                self.logger.warning("No table found on Pandu College notice page.")
                return items

            for row in table.find_all("tr"):
                cells = row.find_all("td")
                # Need at least 3 cells (Sl No, Title, Date)
                if len(cells) < 3:
                    continue

                title = clean_title(cells[1].get_text(strip=True))
                date_str = cells[2].get_text(strip=True)

                if not title or len(title) < 10 or title in seen:
                    continue

                seen.add(title)

                # Resolve file link if present
                file_link = cells[3].find("a", href=True) if len(cells) > 3 else None
                href = file_link["href"].strip() if file_link else ""
                resolved_url = resolve_url(self.BASE_URL, href) if href else self.notice_url

                posted_at = None
                if date_str:
                    # Date is in format YYYY-MM-DD
                    posted_at = parse_date(date_str)

                if not posted_at:
                    posted_at = datetime.now(timezone.utc)

                category = normalize_category(title)
                attachment_url = resolved_url if resolved_url.lower().endswith(".pdf") else None

                items.append({
                    "title": title,
                    "description": f"Pandu College Notice: '{title}'. Sourced from the official Pandu College notice board on {date_str or 'recent'}.",
                    "source_url": resolved_url,
                    "canonical_url": resolved_url,
                    "attachment_url": attachment_url,
                    "category": category,
                    "content_type": category,
                    "posted_at": posted_at,
                    "tags": ["Pandu College", "Guwahati", "Assam", category],
                    "metadata": {
                        "original_page": self.notice_url,
                        "date_string": date_str
                    },
                    "raw_html": str(row)
                })

                if len(items) >= 25:
                    break

        except Exception as e:
            self.logger.error(f"Error scraping Pandu College: {e}")

        return items
