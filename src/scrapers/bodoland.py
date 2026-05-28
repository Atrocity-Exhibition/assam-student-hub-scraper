import re
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup

from scrapers.base_scraper import BaseScraper
from utils.parser_utils import resolve_url, clean_text, parse_date, classify_category
from utils.field_extractor import extract_fields_for_category

class BodolandScraper(BaseScraper):
    def __init__(self):
        super().__init__(
            name="bodoland",
            institution="Bodoland University",
            source="Bodoland University"
        )
        self.base_url = "https://www.buniv.edu.in"
        self.urls = ["https://www.buniv.edu.in/", "http://www.buniv.edu.in/"]
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
                self.logger.info(f"Attempting to fetch Bodoland University home: {url}")
                response = self.fetch_url(url)
                soup = BeautifulSoup(response.text, "html.parser")
                break
            except Exception as e:
                self.logger.warning(f"Could not fetch {url}: {e}")

        if not soup:
            self.logger.error("Failed to fetch Bodoland University website.")
            return items

        for a in soup.select("a"):
            try:
                title = clean_text(a.get_text())
                href = a.get("href", "")
                search_text = title.lower()

                if len(title) < 10 or title in seen:
                    continue

                if any(junk in search_text for junk in self.junk_words):
                    continue

                if not any(k in search_text for k in self.relevant_keywords):
                    continue

                seen.add(title)
                resolved_url = resolve_url(self.base_url, href)

                posted_at = None
                date_match = re.search(r"(\d{2}[-/\.]\d{2}[-/\.]\d{4})", title)
                if date_match:
                    posted_at = parse_date(date_match.group(1))

                category = classify_category(title)
                attachment_url = None
                if resolved_url.lower().endswith(".pdf"):
                    attachment_url = resolved_url

                description = f"Official notification from Bodoland University. Source: {self.source}."
                meta = {
                    "original_source": self.base_url
                }
                extracted_meta = extract_fields_for_category(category, title, description)
                meta.update(extracted_meta)

                items.append({
                    "title": title,
                    "description": description,
                    "source_url": resolved_url,
                    "attachment_url": attachment_url,
                    "category": category,
                    "content_type": category,
                    "posted_at": posted_at,
                    "tags": ["Bodoland University", "BU", category],
                    "metadata": meta,
                    "raw_html": str(a)
                })

                if len(items) >= 25:
                    break
            except Exception as e:
                self.logger.error(f"Error parsing link in Bodoland: {e}")

        return items
