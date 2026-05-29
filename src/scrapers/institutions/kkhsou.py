import re
from datetime import datetime, timezone
from typing import List, Dict, Any
from bs4 import BeautifulSoup

from scrapers.base_scraper import BaseScraper
from utils.parser_utils import resolve_url
from utils.normalizer import clean_title, normalize_date, normalize_category
from utils.field_extractor import extract_fields_for_category

class KKHSOUScraper(BaseScraper):
    SOURCE_NAME = "Krishna Kanta Handiqui State Open University"
    SOURCE_TYPE = "university"
    BASE_URL = "https://kkhsou.ac.in/web/"
    CATEGORY = "mixed"
    SUPPORTED_CONTENT = ["recruitment", "result", "exam", "admission", "notice"]
    RELIABILITY_SCORE = 10

    def __init__(self):
        super().__init__(
            name="kkhsou",
            institution="Krishna Kanta Handiqui State Open University",
            source="KKHSOU"
        )
        # Use precise paths seeded from index research
        self.categories = [
            ("general", "https://kkhsou.ac.in/web/index_news_all.php?c=dEVjS2o0OGV5Sk4yMnBmWHVLTFhvZz09", "notice"),
            ("routines", "https://kkhsou.ac.in/web/index_news_all.php?c=bVc1MXo1YUI3SlZBTEtDZk1RTkFiUT09", "exam"),
            ("recruitments", "https://kkhsou.ac.in/web/index_news_all.php?c=ck1EeldhcUUzNDQyWEdXYmQ3cEZ2UT09", "recruitment"),
            ("results", "https://kkhsou.ac.in/web/index_news_all.php?c=dE9hTkRwd05wc3RrV1JjaTBDQ2VBZz09", "result")
        ]

    def scrape(self) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        seen = set()

        for cat_name, url, default_cat in self.categories:
            try:
                self.logger.info(f"Scraping KKHSOU category {cat_name}: {url}")
                response = self.fetch_url(url)
                soup = BeautifulSoup(response.text, "html.parser")

                tables = soup.find_all("table")
                if not tables:
                    self.logger.warning(f"No tables found on category URL: {url}")
                    continue

                for table in tables:
                    rows = table.find_all("tr")
                    # Skip table header row
                    if len(rows) <= 1:
                        continue

                    for row in rows[1:]:
                        cells = row.find_all("td")
                        if not cells:
                            continue

                        link_tag = row.find("a", href=True)
                        if not link_tag:
                            continue

                        raw_href = link_tag["href"].strip()
                        # Some links are javascript:void(0) or empty
                        if not raw_href or "javascript" in raw_href or raw_href == "#":
                            continue

                        resolved_detail_url = resolve_url(self.BASE_URL, raw_href)
                        row_text = row.get_text(strip=True, separator=" ")

                        # Parse publish date: e.g. "Posted on : May 7, 2026"
                        posted_at = None
                        date_match = re.search(r"Posted\s+on\s*:\s*([A-Za-z]{3}\s+\d{1,2},\s+\d{4})", row_text, re.IGNORECASE)
                        if date_match:
                            posted_at = normalize_date(date_match.group(1))

                        # Fallback for general date patterns
                        if not posted_at:
                            date_pattern_match = re.search(r"(\d{2}[-/\.]\d{2}[-/\.]\d{4})", row_text)
                            if date_pattern_match:
                                posted_at = normalize_date(date_pattern_match.group(1))

                        if not posted_at:
                            posted_at = datetime.now(timezone.utc)

                        # Clean and normalize title (strip "Posted on ..." metadata from title string)
                        title = row_text
                        title = re.sub(r"\s*\|\s*Posted\s+on\s*:.*$", "", title, flags=re.IGNORECASE)
                        title = re.sub(r"\s*Posted\s+on\s*:.*$", "", title, flags=re.IGNORECASE)
                        title = clean_title(title)

                        if not title or len(title) < 10 or title in seen:
                            continue

                        seen.add(title)

                        # Fetch detail page to extract PDF attachment link
                        attachment_url = None
                        try:
                            self.logger.info(f"Fetching detail page: {resolved_detail_url}")
                            detail_res = self.fetch_url(resolved_detail_url)
                            detail_soup = BeautifulSoup(detail_res.text, "html.parser")

                            for a_detail in detail_soup.find_all("a", href=True):
                                detail_href = a_detail["href"].strip()
                                detail_text = a_detail.get_text(strip=True).lower()

                                if "storage/" in detail_href.lower() or detail_href.lower().endswith(".pdf") or "view file" in detail_text:
                                    attachment_url = resolve_url(self.BASE_URL, detail_href)
                                    break
                        except Exception as detail_err:
                            self.logger.error(f"Error fetching detail page {resolved_detail_url}: {detail_err}")

                        # Determine category
                        category = normalize_category(title)
                        if category == "notice":
                            category = default_cat

                        extracted_meta = extract_fields_for_category(category, title, f"Official update from KKHSOU: '{title}'")
                        meta = {
                            "original_category": cat_name,
                            "detail_page_url": resolved_detail_url
                        }
                        meta.update(extracted_meta)

                        items.append({
                            "title": title,
                            "description": f"Official update from KKHSOU: '{title}'. Please refer to the notice details page or attachment for full details.",
                            "source_url": resolved_detail_url,
                            "canonical_url": resolved_detail_url,
                            "attachment_url": attachment_url,
                            "category": category,
                            "content_type": category,
                            "posted_at": posted_at,
                            "tags": ["KKHSOU", "University", "Guwahati", category],
                            "metadata": meta,
                            "raw_html": str(row)
                        })

                        # Cap each run category to prevent excessive fetches in debug/runs
                        if len(items) >= 40:
                            break
                    if len(items) >= 40:
                        break

            except Exception as e:
                self.logger.error(f"Error scraping KKHSOU category {cat_name}: {e}")

        return items
