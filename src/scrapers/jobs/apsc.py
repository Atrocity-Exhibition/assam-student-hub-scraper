from datetime import datetime
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
import requests

from scrapers.base_scraper import BaseScraper
from utils.parser_utils import resolve_url, clean_text, parse_date, classify_category
from utils.field_extractor import extract_fields_for_category

class APSCScraper(BaseScraper):
    def __init__(self, year: Optional[int] = None):
        """
        Initialize the APSC Scraper.
        :param year: Optional calendar year to scrape. Defaults to current year.
        """
        super().__init__(
            name="apsc",
            institution="Assam Public Service Commission",
            institution_slug="assam-public-service-commission"
        )
        self.year = year
        self.base_url = "https://apsc.nic.in"

    def scrape(self) -> List[Dict[str, Any]]:
        """
        Scrapes job advertisements and notifications from APSC.
        """
        results: List[Dict[str, Any]] = []
        year = self.year or datetime.now().year
        
        # 1. Scrape Advertisements Page
        advt_url = f"{self.base_url}/advt_{year}.php"
        try:
            response = self.fetch_url(advt_url)
            advts = self._parse_advertisements(response.text, advt_url)
            results.extend(advts)
            self.logger.info(f"Successfully scraped {len(advts)} advertisements from {advt_url}")
        except requests.HTTPError as he:
            if he.response.status_code == 404:
                self.logger.warning(f"APSC Advertisements page for {year} does not exist yet (404): {advt_url}")
            else:
                self.logger.error(f"HTTP error scraping APSC advertisements: {he}")
        except Exception as e:
            self.logger.error(f"Unexpected error scraping APSC advertisements: {e}")

        # 2. Scrape Notifications Page
        notif_url = f"{self.base_url}/notifications_{year}.php"
        try:
            response = self.fetch_url(notif_url)
            notifs = self._parse_notifications(response.text, notif_url)
            results.extend(notifs)
            self.logger.info(f"Successfully scraped {len(notifs)} notifications from {notif_url}")
        except requests.HTTPError as he:
            if he.response.status_code == 404:
                self.logger.warning(f"APSC Notifications page for {year} does not exist yet (404): {notif_url}")
            else:
                self.logger.error(f"HTTP error scraping APSC notifications: {he}")
        except Exception as e:
            self.logger.error(f"Unexpected error scraping APSC notifications: {e}")

        return results

    def _parse_advertisements(self, html: str, page_url: str) -> List[Dict[str, Any]]:
        """
        Parses the APSC advertisements table.
        Columns: ['Advt. No', 'Post', 'Published Date', 'Closing Date']
        """
        items = []
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        if not table:
            self.logger.warning("No table found on APSC advertisements page.")
            return items

        rows = table.find_all("tr")
        for row in rows:
            cells = row.find_all(["td", "th"])
            if not cells:
                continue
                
            cell_texts = [clean_text(c.get_text()) for c in cells]
            # Skip header row or malformed rows
            if not cell_texts[0] or "Advt. No" in cell_texts[0] or "Advt.No" in cell_texts[0] or len(cells) < 4:
                continue

            advt_no = cell_texts[0]
            post_cell = cells[1]
            published_date_str = cell_texts[2]
            closing_date_str = cell_texts[3]

            # Find the primary link to the advertisement details PDF
            a_tag = post_cell.find("a")
            if not a_tag or not a_tag.get("href"):
                self.logger.debug(f"Skipping row without advertisement link: {cell_texts[1]}")
                continue

            pdf_url = resolve_url(self.base_url, a_tag["href"])
            raw_title = clean_text(a_tag.get_text())
            
            # Combine raw post title and advertisement number for clarity
            title = f"{raw_title} (Advt. No. {advt_no})"
            posted_at = parse_date(published_date_str)
            
            description = f"APSC Advertisement No: {advt_no}. Closing Date for application: {closing_date_str}."
            
            items.append({
                "title": title,
                "description": description,
                "source_url": pdf_url,
                "attachment_url": pdf_url,
                "category": "recruitment",  # Advertisements always represent job vacancies
                "content_type": "recruitment",
                "posted_at": posted_at,
                "tags": [advt_no, "APSC", "job", "recruitment"],
                "raw_html": str(row),
                "metadata": extract_fields_for_category("recruitment", title, description)
            })

        return items

    def _parse_notifications(self, html: str, page_url: str) -> List[Dict[str, Any]]:
        """
        Parses the APSC notifications table.
        Columns: ['SL', 'Notification', 'Date']
        """
        items = []
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        if not table:
            self.logger.warning("No table found on APSC notifications page.")
            return items

        rows = table.find_all("tr")
        for row in rows:
            cells = row.find_all(["td", "th"])
            if not cells:
                continue
                
            cell_texts = [clean_text(c.get_text()) for c in cells]
            # Skip header row or short rows
            if not cell_texts[0] or "SL" in cell_texts[0] or "Serial" in cell_texts[0] or len(cells) < 3:
                continue

            notif_cell = cells[1]
            date_str = cell_texts[2]

            # Find notice PDF attachment link
            a_tag = notif_cell.find("a")
            if not a_tag or not a_tag.get("href"):
                self.logger.debug(f"Skipping notification row without a link: {cell_texts[1]}")
                continue

            pdf_url = resolve_url(self.base_url, a_tag["href"])
            title = clean_text(a_tag.get_text())
            posted_at = parse_date(date_str)
            
            # Dynamic categorization based on title text
            category = classify_category(title)
            
            items.append({
                "title": title,
                "description": f"APSC Notification published on {date_str}.",
                "source_url": pdf_url,
                "attachment_url": pdf_url,
                "category": category,
                "content_type": category,
                "posted_at": posted_at,
                "tags": ["APSC", "notification"],
                "raw_html": str(row),
                "metadata": extract_fields_for_category(category, title, f"APSC Notification published on {date_str}.")
            })

        return items
