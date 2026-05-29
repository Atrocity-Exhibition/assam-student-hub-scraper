import re
from datetime import datetime, timezone
from typing import List, Dict, Any
from bs4 import BeautifulSoup

from scrapers.base_scraper import BaseScraper
from utils.parser_utils import resolve_url
from utils.normalizer import clean_title, normalize_date, normalize_category

class TezpurCollegeScraper(BaseScraper):
    SOURCE_NAME = "Tezpur College"
    SOURCE_TYPE = "university"
    BASE_URL = "https://tezpurcollege.com"
    CATEGORY = "academic"
    SUPPORTED_CONTENT = ["notice", "admission", "exam", "result"]
    RELIABILITY_SCORE = 10

    def __init__(self):
        super().__init__(
            name="tezpur_college",
            institution="Tezpur College",
            source="Tezpur College",
            institution_slug="tezpur-college"
        )
        self.notice_url = "https://tezpurcollege.com/news.php?r=News"

    def scrape(self) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        seen = set()

        try:
            self.logger.info(f"Scraping Tezpur College notices: {self.notice_url}")
            response = self.fetch_url(self.notice_url)
            soup = BeautifulSoup(response.text, "html.parser")

            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                # Tezpur College notice links point to news/...
                if "news/" not in href.lower() and not href.lower().endswith(".pdf"):
                    continue

                raw_title = a.get_text(strip=True)
                # Clean up title by removing common suffixes like "View File", "Download", etc.
                title = re.sub(r"\s*(View File|View pdf|Download|Click Here|New)\s*$", "", raw_title, flags=re.IGNORECASE)
                title = clean_title(title)

                if len(title) < 8 or title in seen:
                    continue

                seen.add(title)
                resolved_url = resolve_url(self.BASE_URL, href)

                posted_at = None
                date_match = re.search(r"(\d{2}[-/\.]\d{2}[-/\.]\d{4})", title)
                if date_match:
                    posted_at = normalize_date(date_match.group(1))

                # If no date in title, try to parse from surrounding text
                if not posted_at:
                    # Look for date in sibling tags or parent td elements
                    parent = a.find_parent(["td", "tr", "p", "div"])
                    if parent:
                        parent_text = parent.get_text()
                        p_date_match = re.search(r"(\d{2}[-/\.]\d{2}[-/\.]\d{4})", parent_text)
                        if p_date_match:
                            posted_at = normalize_date(p_date_match.group(1))

                if not posted_at:
                    posted_at = datetime.now(timezone.utc)

                category = normalize_category(title)
                attachment_url = resolved_url if resolved_url.lower().endswith(".pdf") else None

                items.append({
                    "title": title,
                    "description": f"Official notice from Tezpur College portal: '{title}'.",
                    "source_url": resolved_url,
                    "canonical_url": resolved_url,
                    "attachment_url": attachment_url,
                    "category": category,
                    "content_type": category,
                    "posted_at": posted_at,
                    "tags": ["Tezpur College", "Tezpur", "Sonitpur", category],
                    "metadata": {
                        "original_page": self.notice_url
                    },
                    "raw_html": str(a)
                })

                if len(items) >= 20:
                    break

        except Exception as e:
            self.logger.error(f"Error scraping Tezpur College: {e}")

        return items
