import re
from datetime import datetime, timezone
from typing import List, Dict, Any
from bs4 import BeautifulSoup

from scrapers.base_scraper import BaseScraper
from utils.parser_utils import resolve_url
from utils.normalizer import clean_title, normalize_date, normalize_category

class GHCScraper(BaseScraper):
    SOURCE_NAME = "Gauhati High Court"
    SOURCE_TYPE = "government"
    BASE_URL = "https://ghconline.gov.in"
    CATEGORY = "jobs"
    SUPPORTED_CONTENT = ["recruitment", "result", "exam", "notice"]
    RELIABILITY_SCORE = 10

    def __init__(self):
        super().__init__(
            name="ghc",
            institution="Gauhati High Court",
            source="Gauhati High Court"
        )
        self.target_url = "https://ghconline.gov.in/index.php/recruitment-notices/"

    def scrape(self) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        seen = set()

        try:
            self.logger.info(f"Scraping Gauhati High Court recruitment notices: {self.target_url}")
            response = self.fetch_url(self.target_url)
            soup = BeautifulSoup(response.text, "html.parser")

            # GHC structures notice announcements as separate post-content div cards
            posts = soup.find_all(class_="post-content")
            self.logger.info(f"Found {len(posts)} post-content containers on GHC page")

            for post in posts:
                text = clean_title(post.get_text(strip=True))
                if not text or len(text) < 10 or text in seen:
                    continue

                seen.add(text)

                # Extract date from text (e.g. "Notification dated 19/05/2026 regarding...")
                posted_at = None
                date_match = re.search(r"(\d{2}/\d{2}/\d{4})", text)
                if date_match:
                    posted_at = normalize_date(date_match.group(1))

                if not posted_at:
                    posted_at = datetime.now(timezone.utc)

                # Look for attachments (PDF links) inside this container
                links = post.find_all("a", href=True)
                if not links:
                    continue

                # The first link is typically the main announcement/PDF or application URL
                main_link_el = links[0]
                href = main_link_el["href"].strip()
                resolved_url = resolve_url(self.BASE_URL, href)

                attachment_url = None
                if resolved_url.lower().endswith(".pdf"):
                    attachment_url = resolved_url

                # Put secondary links in metadata
                extra_attachments = []
                for sub_a in links[1:]:
                    sub_href = sub_a["href"].strip()
                    sub_text = clean_title(sub_a.get_text(strip=True))
                    extra_attachments.append({
                        "title": sub_text,
                        "url": resolve_url(self.BASE_URL, sub_href)
                    })

                category = normalize_category(text)
                if category == "notice":
                    category = "recruitment"  # Default to recruitment since we are on the recruitment notices page

                items.append({
                    "title": text,
                    "description": f"Official recruitment notice/order from the Gauhati High Court: '{text}'.",
                    "source_url": resolved_url,
                    "canonical_url": resolved_url,
                    "attachment_url": attachment_url,
                    "category": category,
                    "content_type": category,
                    "posted_at": posted_at,
                    "tags": ["GHC", "Gauhati High Court", "Judiciary", "Govt", category],
                    "metadata": {
                        "original_page": self.target_url,
                        "extra_attachments": extra_attachments
                    },
                    "raw_html": str(post)
                })

                if len(items) >= 40:
                    break

        except Exception as e:
            self.logger.error(f"Error scraping GHC recruitment page: {e}")

        return items
