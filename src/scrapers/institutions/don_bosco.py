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
        self.notice_url = "https://dbuniversity.ac.in/libs/allAnnouncements.php"

    def scrape(self) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        seen = set()

        try:
            self.logger.info(f"Scraping Don Bosco University announcements POST: {self.notice_url}")
            import requests
            from utils.parser_utils import parse_date
            
            response = requests.post(
                self.notice_url,
                data={"Get Announcement": "Get Announcement"},
                headers=self.headers,
                timeout=15,
                verify=False
            )
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            # Parse each <li> element
            for li in soup.find_all("li"):
                a = li.find("a", href=True)
                if not a:
                    continue
                href = a["href"].strip()
                title = clean_title(a.get_text(strip=True))

                # Filter out generic titles or short texts
                if len(title) < 5 or title in seen:
                    continue

                # Filter out general navigation links just in case
                if any(x in title.lower() for x in ["our patron", "why don bosco", "philosophy", "governance", "history", "exchange"]):
                    continue

                seen.add(title)
                resolved_url = resolve_url(self.BASE_URL, href)

                # Attempt to parse date from the title string
                posted_at = None
                # 1. Day Month Name Year (e.g. 14 June 2026)
                m = re.search(r"(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})", title, re.IGNORECASE)
                if m:
                    posted_at = parse_date(m.group(1))
                # 2. Month Name Day, Year (e.g. June 14, 2026)
                if not posted_at:
                    m = re.search(r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})", title, re.IGNORECASE)
                    if m:
                        posted_at = parse_date(m.group(1))
                # 3. Numeric date (e.g. 14-06-2026)
                if not posted_at:
                    m = re.search(r"(\d{1,2}[-/.]\d{1,2}[-/.]\d{4})", title)
                    if m:
                        posted_at = parse_date(m.group(1))
                # 4. Fallback: Year pattern (e.g. 2026)
                if not posted_at:
                    m = re.search(r"\b(202\d)\b", title)
                    if m:
                        try:
                            posted_at = datetime(int(m.group(1)), 1, 1, tzinfo=timezone.utc)
                        except ValueError:
                            pass

                # Ultimate fallback to current date
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
                        "original_page": "https://dbuniversity.ac.in/announcement"
                    },
                    "raw_html": str(li)
                })

                if len(items) >= 40:  # Increase from 20 to 40 to capture all recent announcements
                    break

        except Exception as e:
            self.logger.error(f"Error scraping Don Bosco: {e}")

        return items
