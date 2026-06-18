import re
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup

from scrapers.base_scraper import BaseScraper
from utils.parser_utils import resolve_url, clean_text, parse_date, classify_category

class MangaldaiScraper(BaseScraper):
    def __init__(self):
        super().__init__(
            name="mangaldai",
            institution="Mangaldai College",
            source="Mangaldai College",
            institution_slug="mangaldai-college"
        )
        self.base_url = "https://mangaldaicollege.org"
        self.urls = ["https://mangaldaicollege.org/allNoticeView.php", "https://mangaldaicollege.org/"]
        self.junk_words = [
            "screen reader", "skip to", "main content", "hindi version", 
            "हिंदी", "gallery", "photo", "sitemap", "contact", "about us",
            "accessibility", "rti", "terms", "privacy", "copyright", "home"
        ]
        self.relevant_keywords = [
            "admission", "exam", "result", "routine", "schedule", 
            "recruitment", "vacancy", "notice", "circular", "apply"
        ]

    def scrape(self) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        seen = set()
        soup = None

        for url in self.urls:
            try:
                self.logger.info(f"Attempting to fetch Mangaldai College: {url}")
                response = self.fetch_url(url)
                soup = BeautifulSoup(response.text, "html.parser")
                break
            except Exception as e:
                self.logger.warning(f"Could not fetch {url}: {e}")

        if not soup:
            self.logger.error("Failed to fetch Mangaldai College website.")
            return items

        # Find all message-body div elements representing notice items
        message_bodies = soup.find_all(class_="message-body")
        self.logger.info(f"Found {len(message_bodies)} notice containers (message-body) on Mangaldai page")

        for msg_body in message_bodies:
            try:
                # Find wrapping <a> tag
                a = msg_body.find_parent("a")
                if not a:
                    continue

                href = a.get("href", "").strip()
                if not href:
                    continue

                # Get title from h5
                title_el = msg_body.find("h5")
                if not title_el:
                    continue
                
                title = clean_text(title_el.get_text())
                if len(title) < 5 or title in seen:
                    continue

                seen.add(title)
                resolved_url = resolve_url(self.base_url, href)

                # Parse relative date
                posted_at = None
                span_el = msg_body.find("span")
                if span_el:
                    posted_text = span_el.get_text().strip()
                    # Parse "posted: X Years Y Months Z days ago"
                    match = re.search(r"posted:\s*(?:(\d+)\s*Years?\s*)?(?:(\d+)\s*Months?\s*)?(?:(\d+)\s*days?\s*ago)?", posted_text, re.IGNORECASE)
                    if match:
                        years = int(match.group(1) or 0)
                        months = int(match.group(2) or 0)
                        days = int(match.group(3) or 0)
                        
                        # Fallback/broken epoch dates (e.g. 56 years ago) are ignored
                        if years <= 10:
                            # Calculate date backwards
                            total_days = years * 365 + months * 30 + days
                            from datetime import datetime, timedelta, timezone
                            posted_at = datetime.now(timezone.utc) - timedelta(days=total_days)

                # Fallback to standard date search in title
                if not posted_at:
                    date_match = re.search(r"(\d{2}[-/\.]\d{2}[-/\.]\d{4})", title)
                    if date_match:
                        posted_at = parse_date(date_match.group(1))

                category = classify_category(title)
                attachment_url = None
                if resolved_url.lower().endswith(".pdf"):
                    attachment_url = resolved_url

                items.append({
                    "title": title,
                    "description": f"Official notification from Mangaldai College. Source: {self.source}.",
                    "source_url": resolved_url,
                    "attachment_url": attachment_url,
                    "category": category,
                    "content_type": category,
                    "posted_at": posted_at,
                    "tags": ["Mangaldai College", "MC", category],
                    "metadata": {
                        "original_source": self.base_url
                    },
                    "raw_html": str(msg_body)
                })

            except Exception as e:
                self.logger.error(f"Error parsing notice item in Mangaldai: {e}")

        return items
