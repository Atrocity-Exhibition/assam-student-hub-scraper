import re
from datetime import datetime, timezone
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from scrapers.base_scraper import BaseScraper
from utils.parser_utils import resolve_url
from utils.normalizer import clean_title, normalize_date, normalize_category

class AssamUniversityScraper(BaseScraper):
    SOURCE_NAME = "Assam University, Silchar"
    SOURCE_TYPE = "university"
    BASE_URL = "http://www.aus.ac.in"
    CATEGORY = "mixed"
    SUPPORTED_CONTENT = ["recruitment", "result", "exam", "admission", "scholarship", "notice"]
    RELIABILITY_SCORE = 10

    def __init__(self):
        super().__init__(
            name="assam_university",
            institution="Assam University, Silchar",
            source="Assam University",
            institution_slug="assam-university"
        )
        self.target_url = "http://www.aus.ac.in"
        self.relevant_keywords = [
            "notice", "circular", "advertisement", "recruitment", "vacancy", 
            "admission", "exam", "result", "routine", "schedule", "tender", 
            "corrigendum", "interview", "shortlisted"
        ]

    def scrape(self) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        seen = set()

        # Scrape Homepage (excluding nav/section links, strictly media files)
        self._scrape_homepage(items, seen)

        # Scrape Targeted Recruitment Pages
        self._scrape_recruitment(items, seen, "http://www.aus.ac.in/recruitment-teaching/", "teaching")
        self._scrape_recruitment(items, seen, "http://www.aus.ac.in/recruitment-nonteaching/", "non-teaching")

        return items

    def _scrape_homepage(self, items: List[Dict[str, Any]], seen: set):
        try:
            self.logger.info(f"Scraping Assam University Silchar homepage: {self.target_url}")
            response = self.fetch_url(self.target_url)
            soup = BeautifulSoup(response.text, "html.parser")

            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                
                # Basic check for empty or anchor-only links
                if not href or href.startswith("#") or href == "/" or href.lower() == self.target_url:
                    continue

                title = clean_title(a.get_text(strip=True))
                search_text = title.lower()

                # Basic validity checks
                if len(title) < 10 or title in seen:
                    continue

                # We ONLY accept media file links from the homepage (PDF, images, uploads)
                resolved_url = resolve_url(self.target_url, href)
                
                is_media_file = (
                    resolved_url.lower().endswith(".pdf") or
                    resolved_url.lower().endswith((".jpg", ".jpeg", ".png")) or
                    "/wp-content/uploads/" in resolved_url
                )
                if not is_media_file:
                    continue

                # Relevance check for notices
                is_relevant = any(k in search_text for k in self.relevant_keywords)
                if not is_relevant:
                    continue

                seen.add(title)

                # Date extraction logic: try to parse YYYY/MM from upload paths
                posted_at = None
                date_match = re.search(r"wp-content/uploads/(\d{4})/(\d{2})/", resolved_url)
                if date_match:
                    year = int(date_match.group(1))
                    month = int(date_match.group(2))
                    try:
                        # Default to the first day of that month as posting date
                        posted_at = datetime(year, month, 1, tzinfo=timezone.utc)
                    except ValueError:
                        posted_at = datetime.now(timezone.utc)
                else:
                    # Fallback: check if text has dates like DD-MM-YYYY
                    text_date = re.search(r"(\d{2}[-/\.]\d{2}[-/\.]\d{4})", title)
                    if text_date:
                        posted_at = normalize_date(text_date.group(1))

                # If no date resolved, default to current time
                if not posted_at:
                    posted_at = datetime.now(timezone.utc)

                # Determine category
                category = normalize_category(title)

                attachment_url = None
                if resolved_url.lower().endswith(".pdf"):
                    attachment_url = resolved_url

                items.append({
                    "title": title,
                    "description": f"Official notice from Assam University, Silchar: '{title}'.",
                    "source_url": resolved_url,
                    "canonical_url": resolved_url,
                    "attachment_url": attachment_url,
                    "category": category,
                    "content_type": category,
                    "posted_at": posted_at,
                    "tags": ["Assam University", "AUS", "Silchar", category],
                    "metadata": {
                        "original_page": self.target_url,
                    },
                    "raw_html": str(a)
                })

        except Exception as e:
            self.logger.error(f"Error scraping homepage: {e}")

    def _scrape_recruitment(self, items: List[Dict[str, Any]], seen: set, url: str, recruitment_type: str):
        try:
            self.logger.info(f"Scraping Assam University Silchar {recruitment_type} recruitment page: {url}")
            response = self.fetch_url(url)
            soup = BeautifulSoup(response.text, "html.parser")
            
            table = soup.find("table")
            if not table:
                self.logger.warning(f"No table found on page: {url}")
                return

            rows = table.find_all("tr")
            # Select only leaf rows (avoid duplicates from malformed nested tables)
            leaf_rows = [tr for tr in rows if not tr.find("tr")]

            for idx, tr in enumerate(leaf_rows):
                tds = tr.find_all("td")
                if len(tds) < 4:
                    continue

                # Skip header row if cells contain column titles
                first_cell_text = tds[0].get_text(strip=True).lower()
                second_cell_text = tds[1].get_text(strip=True).lower()
                if "name" in first_cell_text or "description" in second_cell_text:
                    continue

                # Parse Title
                span = tds[1].find("span")
                title_text = span.get_text(strip=True) if span else tds[1].get_text(strip=True)
                title_text = title_text.replace("Link for online application", "").strip()
                title = clean_title(title_text)

                if not title or len(title) < 10 or title in seen:
                    continue

                seen.add(title)

                # Parse dates
                posted_date_str = tds[2].get_text(strip=True)
                last_date_str = tds[3].get_text(strip=True)

                posted_at = normalize_date(posted_date_str)
                if not posted_at:
                    posted_at = datetime.now(timezone.utc)

                # Parse attachments from column 5
                attachment_url = None
                extra_attachments = []
                if len(tds) > 4:
                    links = tds[4].find_all("a", href=True)
                    for link in links:
                        link_text = clean_title(link.get_text(strip=True))
                        link_href = urljoin(url, link["href"].strip())
                        extra_attachments.append({
                            "title": link_text,
                            "url": link_href
                        })
                        # First link matching "advertisement" is set as primary attachment
                        if "advertisement" in link_text.lower() and not attachment_url:
                            attachment_url = link_href

                # Fallback for primary attachment
                if not attachment_url and extra_attachments:
                    attachment_url = extra_attachments[0]["url"]

                # Apply URL inside column 2
                apply_link = tds[1].find("a", href=True)
                apply_url = urljoin(url, apply_link["href"].strip()) if apply_link else None

                # Generate a unique source URL. Prefer attachment_url, then apply_url, else anchor row fallback.
                if attachment_url:
                    source_url = attachment_url
                elif apply_url:
                    source_url = apply_url
                else:
                    source_url = f"{url}#row-{idx}"

                # Category is recruitment
                category = "recruitment"

                metadata = {
                    "original_page": url,
                    "recruitment_type": recruitment_type,
                    "extra_attachments": extra_attachments
                }
                if last_date_str:
                    metadata["last_date"] = last_date_str
                if apply_url:
                    metadata["apply_url"] = apply_url

                items.append({
                    "title": title,
                    "description": f"Official recruitment notice from Assam University: '{title}'.",
                    "source_url": source_url,
                    "canonical_url": source_url,
                    "attachment_url": attachment_url,
                    "category": category,
                    "content_type": category,
                    "posted_at": posted_at,
                    "tags": ["Assam University", "AUS", "Silchar", category, recruitment_type],
                    "metadata": metadata,
                    "raw_html": str(tr)
                })

        except Exception as e:
            self.logger.error(f"Error scraping recruitment from {url}: {e}")
