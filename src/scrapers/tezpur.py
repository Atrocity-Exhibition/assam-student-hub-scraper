import re
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup

from scrapers.base_scraper import BaseScraper
from utils.parser_utils import resolve_url, clean_text, parse_date, classify_category

class TezpurScraper(BaseScraper):
    def __init__(self):
        super().__init__(
            name="tezpur",
            institution="Tezpur University",
            source="Tezpur University"
        )
        self.base_url = "https://www.tezu.ernet.in"
        self.pages = [
            (f"{self.base_url}/other/jobs.htm", "recruitment"),
            (f"{self.base_url}/ProjectWalkin/project_jobs.htm", "recruitment"),
            (f"{self.base_url}/notice/tender.html", "notice"),
            (f"{self.base_url}/AwardsAchievements.html", "notice"),
            (self.base_url, "notice")
        ]
        self.junk_words = ["screen reader", "skip to", "main content", "hindi version", "हिंदी", "gallery", "photo", "sitemap", "contact"]
        self.relevant_keywords = ["admission", "exam", "result", "routine", "schedule", "recruitment", "vacancy", "notice", "circular", "apply"]

    def scrape(self) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        seen = set()

        for page_url, default_cat in self.pages:
            try:
                self.logger.info(f"Scraping Tezpur University page: {page_url}")
                response = self.fetch_url(page_url)
                soup = BeautifulSoup(response.text, "html.parser")

                for a in soup.select("td a, li a, p a, a"):
                    title = clean_text(a.get_text())
                    href = a.get("href", "")
                    search_text = title.lower()

                    if len(title) < 10 or title in seen:
                        continue

                    # Junk filter
                    if any(j in search_text for j in self.junk_words):
                        continue

                    # Relevance filter
                    if not any(k in search_text for k in self.relevant_keywords):
                        continue

                    seen.add(title)

                    resolved_url = resolve_url(page_url, href)

                    # Extract posted date if present in text
                    posted_at = None
                    date_match = re.search(r"(\d{2}[-/\.]\d{2}[-/\.]\d{4})", title)
                    if date_match:
                        posted_at = parse_date(date_match.group(1))

                    # Determine category
                    category = classify_category(title)
                    if category == "notice":
                        category = default_cat

                    attachment_url = None
                    if resolved_url.lower().endswith(".pdf"):
                        attachment_url = resolved_url

                    items.append({
                        "title": title,
                        "description": f"Official notice from Tezpur University. Source: {self.source}.",
                        "source_url": resolved_url,
                        "attachment_url": attachment_url,
                        "category": category,
                        "content_type": category,
                        "posted_at": posted_at,
                        "tags": ["Tezpur University", "TU", category],
                        "metadata": {
                            "original_page": page_url
                        },
                        "raw_html": str(a)
                    })

                    if len(items) >= 40:
                        break

            except Exception as e:
                self.logger.error(f"Error scraping {page_url}: {e}")

        return items
