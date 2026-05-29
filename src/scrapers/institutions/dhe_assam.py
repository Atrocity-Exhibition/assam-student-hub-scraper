import re
import os
import urllib.parse
from datetime import datetime, timezone
from typing import List, Dict, Any
from bs4 import BeautifulSoup

from scrapers.base_scraper import BaseScraper
from utils.parser_utils import resolve_url
from utils.normalizer import clean_title, normalize_date, normalize_category

class DHEAssamScraper(BaseScraper):
    SOURCE_NAME = "Directorate of Higher Education, Assam"
    SOURCE_TYPE = "government"
    BASE_URL = "https://directorateofhighereducation.assam.gov.in"
    CATEGORY = "academic"
    SUPPORTED_CONTENT = ["scholarship", "notice"]
    RELIABILITY_SCORE = 10

    def __init__(self):
        super().__init__(
            name="dhe_assam",
            institution="Directorate of Higher Education, Assam",
            source="DHE Assam",
            institution_slug="dhe-assam"
        )
        self.taxonomy_url = f"{self.BASE_URL}/taxonomy/term/5666"
        self.notifications_url = f"{self.BASE_URL}/documents/notifications-2"

    def scrape(self) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        seen_urls = set()

        # 1. Scrape DHE Scholarships Taxonomy Page (direct scholarship application files)
        try:
            self.logger.info(f"Scraping DHE Scholarships taxonomy page: {self.taxonomy_url}")
            response = self.fetch_url(self.taxonomy_url)
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Extract links inside views
            views = soup.select(".view-content")
            if views:
                # View 0 typically has the main scholarship application / guideline links
                for a in views[0].find_all("a", href=True):
                    href = a["href"].strip()
                    resolved_url = resolve_url(self.BASE_URL, href)
                    
                    if resolved_url in seen_urls:
                        continue
                        
                    raw_text = a.get_text().strip()
                    if not raw_text:
                        # Fallback: extract title from decoded PDF filename if link text is empty
                        filename = os.path.basename(resolved_url)
                        raw_text = urllib.parse.unquote(filename).replace(".pdf", "").replace("-", " ").replace("_", " ")
                        
                    title = clean_title(raw_text)
                    if len(title) < 5 or "apply" in title.lower():
                        if "apply" in title.lower() and "scholarship" not in title.lower():
                            title = f"Apply for DHE Assam Scholarship: {title}"
                            
                    # Attempt to resolve date from text or use fallback
                    posted_at = datetime.now(timezone.utc)
                    
                    attachment_url = resolved_url if resolved_url.lower().endswith(".pdf") else None
                    category = "scholarship"  # Always scholarship on this taxonomy page
                    
                    seen_urls.add(resolved_url)
                    items.append({
                        "title": title,
                        "description": f"Official scholarship guidelines or application details: '{title}' published by Directorate of Higher Education, Assam.",
                        "source_url": resolved_url,
                        "canonical_url": resolved_url,
                        "attachment_url": attachment_url,
                        "category": category,
                        "content_type": category,
                        "posted_at": posted_at,
                        "tags": ["DHE Assam", "Scholarship", "Assam Government", "Higher Education"],
                        "metadata": {
                            "original_page": self.taxonomy_url,
                            "section": "Scholarships Board"
                        },
                        "raw_html": str(a)
                    })
        except Exception as e:
            self.logger.error(f"Error scraping DHE Scholarships taxonomy: {e}")

        # 2. Scrape general DHE notifications list and filter for scholarship announcements
        try:
            self.logger.info(f"Scraping DHE Notifications feed: {self.notifications_url}")
            response = self.fetch_url(self.notifications_url)
            soup = BeautifulSoup(response.text, "html.parser")
            
            views = soup.select(".view-content")
            if len(views) > 1:
                # View 1 contains the notifications list
                list_container = views[1]
                list_items = list_container.find_all("li")
                
                self.logger.info(f"Found {len(list_items)} list items in DHE notifications feed")
                for li in list_items:
                    title_field = li.select_one(".views-field-title a")
                    if not title_field or not title_field.get("href"):
                        continue
                        
                    list_title = clean_title(title_field.get_text().strip())
                    detail_href = title_field["href"].strip()
                    detail_url = resolve_url(self.BASE_URL, detail_href)
                    
                    if detail_url in seen_urls:
                        continue
                        
                    # Filter for scholarship related keywords
                    title_lower = list_title.lower()
                    keywords = ["scholarship", "merit", "stipend", "fellowship", "grant", "fee waiver", "aasoni", "fee concession", "nijut"]
                    if not any(k in title_lower for k in keywords):
                        continue
                        
                    self.logger.info(f"Found matching notification: '{list_title}' -> details at {detail_url}")
                    
                    # Fetch detail page to extract title and download PDF attachment
                    try:
                        detail_resp = self.fetch_url(detail_url)
                        detail_soup = BeautifulSoup(detail_resp.text, "html.parser")
                        
                        # Extract clean title from detail page (the second h1 is usually the document title)
                        h1_elements = detail_soup.find_all("h1")
                        clean_title_text = list_title
                        if len(h1_elements) > 1:
                            clean_title_text = clean_title(h1_elements[1].get_text().strip())
                        elif detail_soup.title:
                            clean_title_text = clean_title(detail_soup.title.string.split("|")[0].strip())
                            
                        # Extract attachment links pointing to PDFs
                        attachment_url = None
                        for a_attach in detail_soup.find_all("a", href=True):
                            a_href = a_attach["href"].strip()
                            if a_href.lower().endswith(".pdf") or "download" in a_href.lower() or "show-file" in a_href.lower():
                                attachment_url = resolve_url(self.BASE_URL, a_href)
                                break
                                
                        # Extract date from title text or detail page update timestamp
                        posted_at = None
                        date_match = re.search(r"(\d{2}[-/\.]\d{2}[-/\.]\d{4})", clean_title_text)
                        if date_match:
                            posted_at = normalize_date(date_match.group(1))
                            
                        if not posted_at:
                            # Try to parse from DHE "Last Reviewed & Updated" string
                            last_update_el = detail_soup.select_one(".swf-last-update")
                            if last_update_el:
                                update_text = last_update_el.get_text().strip()
                                # e.g. "Last Reviewed & Updated: 23 Mar 2026"
                                date_str_match = re.search(r"Updated:\s*(.+)$", update_text, re.IGNORECASE)
                                if date_str_match:
                                    posted_at = normalize_date(date_str_match.group(1))
                                    
                        if not posted_at:
                            # Fallback to current time
                            posted_at = datetime.now(timezone.utc)
                            
                        category = normalize_category(clean_title_text)
                        seen_urls.add(detail_url)
                        
                        items.append({
                            "title": clean_title_text,
                            "description": f"Official notification published by Directorate of Higher Education, Assam: '{clean_title_text}'. Check details or download the official circular.",
                            "source_url": detail_url,
                            "canonical_url": detail_url,
                            "attachment_url": attachment_url,
                            "category": category,
                            "content_type": category,
                            "posted_at": posted_at,
                            "tags": ["DHE Assam", "Scholarship", "Assam Government", "Higher Education", category],
                            "metadata": {
                                "original_page": self.notifications_url,
                                "section": "Notifications Feed"
                            },
                            "raw_html": str(li)
                        })
                        
                    except Exception as details_err:
                        self.logger.error(f"Error fetching details from {detail_url}: {details_err}")
                        
        except Exception as e:
            self.logger.error(f"Error scraping DHE general notifications feed: {e}")

        return items
