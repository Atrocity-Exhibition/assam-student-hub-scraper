import re
from datetime import datetime, timezone
from typing import List, Dict, Any
from bs4 import BeautifulSoup

from scrapers.base_scraper import BaseScraper
from utils.parser_utils import resolve_url
from utils.normalizer import clean_title, normalize_date, normalize_category

class ADTUScraper(BaseScraper):
    SOURCE_NAME = "Assam Down Town University"
    SOURCE_TYPE = "university"
    BASE_URL = "https://adtu.in"
    CATEGORY = "academic"
    SUPPORTED_CONTENT = ["notice", "admission", "exam", "result"]
    RELIABILITY_SCORE = 10

    def __init__(self):
        super().__init__(
            name="adtu",
            institution="Assam Down Town University",
            source="ADTU",
            institution_slug="assam-down-town-university"
        )
        self.targets = [
            "https://adtu.in",
            "https://adtu.in/news-and-events/"
        ]

    def scrape(self) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        seen = set()

        for url in self.targets:
            try:
                self.logger.info(f"Scraping ADTU page: {url}")
                response = self.fetch_url(url)
                soup = BeautifulSoup(response.text, "html.parser")

                for a in soup.find_all("a", href=True):
                    href = a["href"].strip()
                    # Resolve scheme-relative URLs
                    if href.startswith("//"):
                        resolved_url = "https:" + href
                    else:
                        resolved_url = resolve_url(self.BASE_URL, href)

                    # Look for circular PDFs, news-details, or tender-notices
                    is_notice = any(x in href.lower() for x in ["news-details", "circular", ".pdf", "tender-notice"])
                    if not is_notice:
                        continue

                    raw_text = a.get_text(strip=True)
                    title = clean_title(raw_text)

                    # If text is truncated or generic, parse slug
                    if not title or title.lower() in ["read more", "view all", "click here", "placement", "news & events", "tender notice"]:
                        slug_match = re.search(r"news-details/([a-z0-9\-]{15,100})$", href)
                        if slug_match:
                            title = clean_title(slug_match.group(1).replace("-", " ").capitalize())
                        else:
                            # Try general pdf filename
                            pdf_match = re.search(r"/([^/]+)\.pdf$", href)
                            if pdf_match:
                                title = clean_title(pdf_match.group(1).replace("-", " ").replace("_", " ").capitalize())
                            else:
                                continue

                    if len(title) < 12 or title in seen:
                        continue

                    # Filter out static navigation/social links
                    if any(x in title.lower() for x in ["instagram", "facebook", "twitter", "linkedin", "apply now"]):
                        continue

                    seen.add(title)

                    # Date extraction
                    posted_at = None
                    # Try to match date inside filename: e.g. 02-01-2025-CIRCULAR-...
                    date_match = re.search(r"(\d{2}[-/\.]\d{2}[-/\.]\d{4})", resolved_url)
                    if date_match:
                        posted_at = normalize_date(date_match.group(1))

                    if not posted_at:
                        posted_at = datetime.now(timezone.utc)

                    category = normalize_category(title)
                    attachment_url = resolved_url if resolved_url.lower().endswith(".pdf") else None

                    items.append({
                        "title": title,
                        "description": f"Circular and news announcement from Assam Down Town University: '{title}'.",
                        "source_url": resolved_url,
                        "canonical_url": resolved_url,
                        "attachment_url": attachment_url,
                        "category": category,
                        "content_type": category,
                        "posted_at": posted_at,
                        "tags": ["ADTU", "Assam Down Town University", "Guwahati", category],
                        "metadata": {
                            "original_page": url
                        },
                        "raw_html": str(a)
                    })

                    if len(items) >= 20:
                        break

            except Exception as e:
                self.logger.error(f"Error scraping ADTU page {url}: {e}")

        return items
