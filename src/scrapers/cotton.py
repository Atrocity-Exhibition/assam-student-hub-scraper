import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
import requests

from scrapers.base_scraper import BaseScraper
from utils.parser_utils import resolve_url, clean_text, parse_date, classify_category
from utils.field_extractor import extract_fields_for_category

class CottonScraper(BaseScraper):
    def __init__(self, limit: Optional[int] = 15):
        """
        Initialize the Cotton University Scraper.
        :param limit: Maximum number of detail pages to fetch per category to avoid long crawling times.
        """
        super().__init__(
            name="cotton",
            institution="Cotton University",
            source="Cotton University"
        )
        self.limit = limit
        self.base_url = "https://cottonuniversity.ac.in/"
        self.category_urls = {
            "notice": "https://cottonuniversity.ac.in/index_news_category.php?c=eExGNStiZHp6MmpnVGlUQ2pmQU5pdz09",
            "recruitment": "https://cottonuniversity.ac.in/index_news_category.php?c=elN5S25McE1zYTRuQm1WcStNYmZmQT09"
        }

    def scrape(self) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []

        for default_cat, url in self.category_urls.items():
            try:
                self.logger.info(f"Scraping Cotton University category page: {url}")
                response = self.fetch_url(url)
                items = self._parse_category_page(response.text, default_cat)
                results.extend(items)
                self.logger.info(f"Successfully scraped {len(items)} notices from {url}")
            except Exception as e:
                self.logger.error(f"Error scraping Cotton University category {default_cat}: {e}")

        return results

    def _parse_category_page(self, html: str, default_cat: str) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        soup = BeautifulSoup(html, "html.parser")
        
        # Find all tables with class "display"
        tables = soup.find_all("table", class_="display")
        if not tables:
            tables = soup.find_all("table")

        if not tables:
            self.logger.warning("No tables found on Cotton University category page.")
            return items

        # Collect raw rows across all display tables (each table represents a year group)
        raw_rows = []
        for table in tables:
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all(["td", "th"])
                if not cells:
                    continue
                # Skip headers
                cell_text = clean_text(row.get_text())
                if "General Notifications" in cell_text or "Recruitment" in cell_text or not cell_text:
                    continue
                
                # Check for detail links
                a_tag = row.find("a", href=True)
                if a_tag and ("index_post_details" in a_tag["href"] or "news_details" in a_tag["href"]):
                    raw_rows.append((row, a_tag))

        self.logger.info(f"Found {len(raw_rows)} total rows on index page. Crawling top {self.limit} records.")

        # Limit detail page scraping to avoid long wait times
        crawled_count = 0
        for row, a_tag in raw_rows:
            if self.limit and crawled_count >= self.limit:
                self.logger.info(f"Reached limit of {self.limit} detail page requests for this category.")
                break

            try:
                raw_title = clean_text(a_tag.get_text())
                detail_href = a_tag["href"]
                detail_url = resolve_url(self.base_url, detail_href)
                
                # Extract posted date from row text
                row_text = row.get_text()
                posted_at = None
                date_match = re.search(r"Posted\s+on\s*:\s*([A-Za-z]{3}\s+\d{1,2},\s+\d{4})", row_text, re.IGNORECASE)
                if date_match:
                    date_str = date_match.group(1)
                    posted_at = parse_date(date_str)
                
                # Dynamically classify category
                category = classify_category(raw_title)
                if category == "notice" and default_cat:
                    category = default_cat

                # Polite fetch of the detail page to extract pdf attachment
                self.logger.info(f"Fetching detail page: {detail_url}")
                detail_response = self.fetch_url(detail_url)
                attachment_url = self._parse_detail_page(detail_response.text)
                
                crawled_count += 1
                
                # Deduplication key is source_url (the detail page URL)
                source_url = detail_url
                
                description = f"Official Notification from Cotton University. Published date: {posted_at.strftime('%Y-%m-%d') if posted_at else 'Unknown'}."

                items.append({
                    "title": raw_title,
                    "description": description,
                    "source_url": source_url,
                    "attachment_url": attachment_url,
                    "category": category,
                    "content_type": category,
                    "posted_at": posted_at,
                    "tags": ["Cotton University", "CU", category],
                    "raw_html": str(row),
                    "metadata": extract_fields_for_category(category, raw_title, description)
                })

            except Exception as e:
                self.logger.error(f"Failed to scrape Cotton detail page {a_tag.get('href') if a_tag else 'unknown'}: {e}")

        return items

    def _parse_detail_page(self, html: str) -> Optional[str]:
        """
        Parses the detail page to find the PDF attachment URL inside the '.entry-content' container.
        """
        soup = BeautifulSoup(html, "html.parser")
        entry_content = soup.find(class_="entry-content")
        if not entry_content:
            return None

        # Look for PDF links
        pdf_links = entry_content.find_all("a", href=re.compile(r"\.pdf", re.IGNORECASE))
        if pdf_links:
            # Return first resolved PDF URL
            return resolve_url(self.base_url, pdf_links[0]["href"])

        # Alternate check: any link pointing to storage/uploads
        uploads_links = entry_content.find_all("a", href=re.compile(r"storage/uploads/", re.IGNORECASE))
        if uploads_links:
            return resolve_url(self.base_url, uploads_links[0]["href"])

        return None
