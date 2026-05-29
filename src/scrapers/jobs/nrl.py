import re
from datetime import datetime, timezone
from typing import List, Dict, Any
from bs4 import BeautifulSoup

from scrapers.base_scraper import BaseScraper
from utils.parser_utils import resolve_url
from utils.normalizer import clean_title, normalize_date

class NRLScraper(BaseScraper):
    SOURCE_NAME = "Numaligarh Refinery Limited"
    SOURCE_TYPE = "government"  # Public Sector Undertaking
    BASE_URL = "https://portal2.nrl.co.in/onlineapp/"
    CATEGORY = "jobs"
    SUPPORTED_CONTENT = ["recruitment"]
    RELIABILITY_SCORE = 10

    def __init__(self):
        super().__init__(
            name="nrl",
            institution="Numaligarh Refinery Limited",
            source="NRL"
        )
        self.pages = [
            "https://portal2.nrl.co.in/onlineapp/Home/CurrentOpenings",
            "https://portal2.nrl.co.in/onlineapp/Home/ContractualCurrentOportunities"
        ]

    def scrape(self) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        seen = set()

        for page_url in self.pages:
            try:
                self.logger.info(f"Scraping NRL page: {page_url}")
                response = self.fetch_url(page_url)
                soup = BeautifulSoup(response.text, "html.parser")

                # Notices are encapsulated in left-flex divs on both layouts
                blocks = soup.find_all(class_="left-flex")
                self.logger.info(f"Found {len(blocks)} left-flex job blocks on {page_url}")

                for block in blocks:
                    # Parse date from the logo container: e.g. "May 5 2026"
                    date_div = block.find(class_="job-logo")
                    posted_at = None
                    if date_div:
                        date_text = " ".join(date_div.get_text(separator=" ").split())
                        if date_text:
                            # Strip any stray hyphens or horizontal lines
                            date_cleaned = re.sub(r'[\s\-]+', ' ', date_text).strip()
                            posted_at = normalize_date(date_cleaned)
                    if not posted_at:
                        posted_at = datetime.now(timezone.utc)

                    # Extract job content block
                    content_div = block.find(class_="job-content")
                    if not content_div:
                        continue

                    title_tag = content_div.find("h6") or content_div.find(class_="heading")
                    if not title_tag:
                        continue

                    title = clean_title(title_tag.get_text(strip=True))
                    if not title or len(title) < 10 or title in seen:
                        continue

                    seen.add(title)

                    # Extract detailed advertisement PDF link
                    attachment_url = None
                    for a in content_div.find_all("a", href=True):
                        href = a["href"].strip()
                        if "DownloadFile" in href:
                            attachment_url = resolve_url(self.BASE_URL, href)
                            break

                    description = f"Job vacancy announced by Numaligarh Refinery Limited: '{title}'. Please refer to the official application portal for full terms and to apply online."

                    items.append({
                        "title": title,
                        "description": description,
                        "source_url": page_url,
                        "canonical_url": page_url,
                        "attachment_url": attachment_url,
                        "category": "recruitment",
                        "content_type": "recruitment",
                        "posted_at": posted_at,
                        "tags": ["NRL", "PSU", "Numaligarh", "Golaghat", "Jobs", "Recruitment"],
                        "metadata": {
                            "source_page": page_url
                        },
                        "raw_html": str(block)
                    })

            except Exception as e:
                self.logger.error(f"Error scraping NRL page {page_url}: {e}")

        return items
