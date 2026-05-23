import re
from datetime import datetime, timezone
from typing import List, Dict, Any
from bs4 import BeautifulSoup

from scrapers.base_scraper import BaseScraper
from utils.parser_utils import resolve_url
from utils.normalizer import clean_title, normalize_date, normalize_category

class ASTUScraper(BaseScraper):
    SOURCE_NAME = "Assam Science and Technology University"
    SOURCE_TYPE = "university"
    BASE_URL = "https://astu.ac.in"
    CATEGORY = "mixed"
    SUPPORTED_CONTENT = ["recruitment", "result", "exam", "admission", "scholarship", "notice"]
    RELIABILITY_SCORE = 10

    def __init__(self):
        super().__init__(
            name="astu",
            institution="Assam Science and Technology University",
            source="ASTU"
        )
        self.pages = [
            ("https://astu.ac.in/?page_id=561", "notice"),       # News & Notifications
            ("https://astu.ac.in/?page_id=735", "exam"),         # Exam Notification
            ("https://astu.ac.in/?page_id=110", "recruitment"),  # Recruitments
        ]

    def scrape(self) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        seen = set()

        for page_url, default_cat in self.pages:
            try:
                self.logger.info(f"Scraping ASTU page: {page_url}")
                response = self.fetch_url(page_url)
                soup = BeautifulSoup(response.text, "html.parser")

                # Find notifications container
                container = soup.find(class_="box-frame-in")
                if not container:
                    container = soup.find(id="primary") or soup.find(id="content") or soup

                for a in container.find_all("a", href=True):
                    href = a["href"].strip()
                    title = clean_title(a.get_text(strip=True))

                    # Basic validity check
                    if len(title) < 10 or title in seen:
                        continue

                    # Filter out helper pages and navigation links
                    if any(x in href.lower() for x in ["page_id=15", "page_id=17", "page_id=21", "page_id=27", "page_id=9"]):
                        continue

                    seen.add(title)

                    resolved_url = resolve_url(self.BASE_URL, href)

                    # Extract posted date if present in title string
                    # ASTU commonly lists dates like: "Notification regarding ... - 19-01-2019"
                    posted_at = None
                    date_match = re.search(r"(\d{2}[-/\.]\d{2}[-/\.]\d{4})", title)
                    if date_match:
                        posted_at = normalize_date(date_match.group(1))

                    # Fallback to upload folder structure
                    if not posted_at:
                        upload_match = re.search(r"wp-content/uploads/(\d{4})/(\d{2})/", resolved_url)
                        if upload_match:
                            year = int(upload_match.group(1))
                            month = int(upload_match.group(2))
                            try:
                                posted_at = datetime(year, month, 1, tzinfo=timezone.utc)
                            except ValueError:
                                posted_at = datetime.now(timezone.utc)

                    # Final fallback to current time
                    if not posted_at:
                        posted_at = datetime.now(timezone.utc)

                    # Determine category
                    category = normalize_category(title)
                    if category == "notice":
                        category = default_cat

                    attachment_url = None
                    if resolved_url.lower().endswith(".pdf"):
                        attachment_url = resolved_url

                    items.append({
                        "title": title,
                        "description": f"Official update from ASTU: '{title}'. Sourced from ASTU Portal.",
                        "source_url": resolved_url,
                        "canonical_url": resolved_url,
                        "attachment_url": attachment_url,
                        "category": category,
                        "content_type": category,
                        "posted_at": posted_at,
                        "tags": ["ASTU", "University", "Guwahati", category],
                        "metadata": {
                            "original_page": page_url,
                        },
                        "raw_html": str(a)
                    })

                    if len(items) >= 40:
                        break

            except Exception as e:
                self.logger.error(f"Error scraping ASTU page {page_url}: {e}")

        return items
