import re
from datetime import datetime, timezone
from typing import List, Dict, Any
from bs4 import BeautifulSoup

from scrapers.base_scraper import BaseScraper
from utils.parser_utils import resolve_url
from utils.normalizer import clean_title, normalize_date, normalize_category

class LOKDCollegeScraper(BaseScraper):
    SOURCE_NAME = "LOKD College"
    SOURCE_TYPE = "university"
    BASE_URL = "https://lokdcollegeonline.co.in"
    CATEGORY = "academic"
    SUPPORTED_CONTENT = ["notice", "admission", "exam", "result"]
    RELIABILITY_SCORE = 10

    def __init__(self):
        super().__init__(
            name="lokd_college",
            institution="LOKD College",
            source="LOKD College",
            institution_slug="lokd-college"
        )
        self.notice_url = "https://lokdcollegeonline.co.in"

    def scrape(self) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        seen = set()

        try:
            self.logger.info(f"Scraping LOKD College portal: {self.notice_url}")
            response = self.fetch_url(self.notice_url)
            soup = BeautifulSoup(response.text, "html.parser")

            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                # Check for files in upload paths or direct pdf/images
                if not any(x in href.lower() for x in ["upload/", "notice", ".pdf", ".jpeg", ".jpg", ".png"]):
                    continue

                if "online_notice.php" in href:
                    continue

                raw_link_text = a.get_text(strip=True)
                title = clean_title(raw_link_text)

                # If link text is "Click Here" or generic, look at parent text
                if not title or title.lower() in ["click here", "view", "download", "click"]:
                    parent = a.find_parent(["tr", "td", "li", "div", "p"])
                    if parent:
                        # Extract all text in the parent container, except the link text itself
                        parent_text = parent.get_text(" ", strip=True)
                        parent_text_clean = re.sub(r"\s*(click here|view|download|click)\s*$", "", parent_text, flags=re.IGNORECASE)
                        title = clean_title(parent_text_clean)

                if len(title) < 10 or title in seen:
                    continue

                seen.add(title)
                resolved_url = resolve_url(self.BASE_URL, href)

                # Try to extract a date
                posted_at = None
                date_match = re.search(r"(\d{2}[-/\.]\d{2}[-/\.]\d{4})", title)
                if date_match:
                    posted_at = normalize_date(date_match.group(1))

                # Check for upload timestamp in filename
                if not posted_at:
                    ts_match = re.search(r"/(\d{9,10})", resolved_url)
                    if ts_match:
                        try:
                            posted_at = datetime.fromtimestamp(int(ts_match.group(1)), tz=timezone.utc)
                        except (ValueError, OverflowError):
                            pass

                if not posted_at:
                    posted_at = datetime.now(timezone.utc)

                category = normalize_category(title)
                attachment_url = resolved_url if any(resolved_url.lower().endswith(ext) for ext in [".pdf", ".jpeg", ".jpg", ".png"]) else None

                items.append({
                    "title": title,
                    "description": f"Official announcement from Loknayak Omeo Kumar Das College: '{title}'. Check the college portal for additional instructions.",
                    "source_url": resolved_url,
                    "canonical_url": resolved_url,
                    "attachment_url": attachment_url,
                    "category": category,
                    "content_type": category,
                    "posted_at": posted_at,
                    "tags": ["LOKD College", "Dhekiajuli", "Sonitpur", category],
                    "metadata": {
                        "original_page": self.notice_url
                    },
                    "raw_html": str(parent) if 'parent' in locals() and parent else str(a)
                })

                if len(items) >= 20:
                    break

        except Exception as e:
            self.logger.error(f"Error scraping LOKD College notices: {e}")

        return items
