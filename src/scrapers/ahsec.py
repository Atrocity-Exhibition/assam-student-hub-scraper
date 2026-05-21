import re
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup

from scrapers.base_scraper import BaseScraper
from utils.parser_utils import resolve_url, clean_text, parse_date, classify_category

class AHSECScraper(BaseScraper):
    def __init__(self):
        super().__init__(
            name="ahsec",
            institution="Assam Higher Secondary Education Council",
            source="AHSEC Official"
        )
        self.base_url = "https://ahsec.assam.gov.in"
        self.urls = ["https://ahsec.assam.gov.in/"]
        self.relevant_keywords = ["exam", "examination", "routine", "schedule", "result", "notification", "admit", "date", "hs", "higher secondary", "ahsec"]
        self.junk_keywords = ["home", "about", "contact", "login", "news"]

    def scrape(self) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        seen = set()
        soup = None

        for url in self.urls:
            try:
                self.logger.info(f"Fetching AHSEC homepage: {url}")
                response = self.fetch_url(url)
                soup = BeautifulSoup(response.text, "html.parser")
                break
            except Exception as e:
                self.logger.warning(f"Could not fetch {url}: {e}")

        if not soup:
            self.logger.error("Failed to fetch AHSEC website.")
            return items

        for a in soup.select("a"):
            try:
                title = clean_text(a.get_text())
                href = a.get("href", "")
                search_text = title.lower()

                if len(title) < 10 or title in seen:
                    continue

                if not any(k in search_text for k in self.relevant_keywords):
                    continue

                if any(s in search_text for s in self.junk_keywords):
                    continue

                seen.add(title)
                resolved_url = resolve_url(self.base_url, href)

                posted_at = None
                date_match = re.search(r"(\d{2}[-/\.]\d{2}[-/\.]\d{4})", title)
                if date_match:
                    posted_at = parse_date(date_match.group(1))

                category = classify_category(title)
                if category == "notice":
                    category = "exam"

                attachment_url = None
                if resolved_url.lower().endswith(".pdf"):
                    attachment_url = resolved_url

                items.append({
                    "title": title,
                    "description": f"AHSEC notification: {title}. Check ahsec.assam.gov.in for full schedule and details.",
                    "source_url": resolved_url,
                    "attachment_url": attachment_url,
                    "category": category,
                    "content_type": category,
                    "posted_at": posted_at,
                    "tags": ["AHSEC", "Board Exam", "Assam Board", category],
                    "metadata": {
                        "streams": "Arts / Science / Commerce",
                        "original_source": self.base_url
                    },
                    "raw_html": str(a)
                })

                if len(items) >= 15:
                    break
            except Exception as e:
                self.logger.error(f"Error parsing link in AHSEC: {e}")

        return items
