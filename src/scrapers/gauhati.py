import re
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
import requests

from scrapers.base_scraper import BaseScraper
from utils.parser_utils import resolve_url, clean_text, parse_date, classify_category
from utils.slug import slugify

class GauhatiScraper(BaseScraper):
    def __init__(self):
        super().__init__(
            name="gauhati",
            institution="Gauhati University",
            source="Gauhati University"
        )
        self.exam_url = "https://sites.google.com/a/gauhati.ac.in/notifications/examination"
        self.recruitment_url = "https://sites.google.com/a/gauhati.ac.in/notifications/recruitment/recruitment"

    def scrape(self) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []

        # 1. Scrape Exam Notifications
        try:
            self.logger.info(f"Scraping Gauhati University Exam page: {self.exam_url}")
            response = self.fetch_url(self.exam_url)
            exam_notices = self._parse_google_sites_page(response.text, self.exam_url, default_category="exam")
            results.extend(exam_notices)
            self.logger.info(f"Successfully scraped {len(exam_notices)} exam notices from {self.exam_url}")
        except Exception as e:
            self.logger.error(f"Error scraping Gauhati Exam notices: {e}")

        # 2. Scrape Recruitment Notifications
        try:
            self.logger.info(f"Scraping Gauhati University Recruitment page: {self.recruitment_url}")
            response = self.fetch_url(self.recruitment_url)
            recruitment_notices = self._parse_google_sites_page(response.text, self.recruitment_url, default_category="recruitment")
            results.extend(recruitment_notices)
            self.logger.info(f"Successfully scraped {len(recruitment_notices)} recruitment notices from {self.recruitment_url}")
        except Exception as e:
            self.logger.error(f"Error scraping Gauhati Recruitment notices: {e}")

        return results

    def _parse_google_sites_page(self, html: str, page_url: str, default_category: str) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        soup = BeautifulSoup(html, "html.parser")
        
        # Google Sites packages text fragments and titles inside .tyJCtd elements
        blocks = soup.find_all("div", class_="tyJCtd")
        if not blocks:
            self.logger.warning(f"No content blocks (class 'tyJCtd') found on page: {page_url}")
            return items

        notices = []
        current_notice = None

        for block in blocks:
            text = block.get_text().strip()
            text_clean = " ".join(text.split())
            if not text_clean:
                # If block is empty, inspect for attachments/links
                links = block.find_all("a", href=True)
                if links and current_notice:
                    for l in links:
                        href = l["href"]
                        txt = clean_text(l.get_text(strip=True))
                        # Identify Drive / PDF attachments
                        if "drive.google.com" in href or "file/d/" in href or ".pdf" in href.lower():
                            current_notice["attachments"].append((txt, href))
                continue

            # Check if block matches a date in DD-MM-YYYY format
            match_date = re.match(r"^(\d{2}-\d{2}-\d{4})$", text_clean)
            if match_date:
                if current_notice:
                    notices.append(current_notice)
                current_notice = {
                    "date": text_clean,
                    "title": "",
                    "links": [],
                    "attachments": []
                }
            else:
                if current_notice:
                    if not current_notice["title"]:
                        current_notice["title"] = text_clean
                        links = block.find_all("a", href=True)
                        for l in links:
                            current_notice["links"].append((clean_text(l.get_text(strip=True)), l["href"]))
                    else:
                        links = block.find_all("a", href=True)
                        if links:
                            for l in links:
                                href = l["href"]
                                txt = clean_text(l.get_text(strip=True))
                                if "drive.google.com" in href or "file/d/" in href or ".pdf" in href.lower():
                                    current_notice["attachments"].append((txt, href))
                                else:
                                    current_notice["links"].append((txt, href))
                        else:
                            current_notice["title"] += " | " + text_clean

        if current_notice:
            notices.append(current_notice)

        # Build notice items
        for n in notices:
            title = n["title"]
            if not title:
                self.logger.debug(f"Skipping notice with date {n['date']} but empty title")
                continue

            posted_at = parse_date(n["date"])
            if posted_at and posted_at.year < 2024:
                self.logger.debug(f"Skipping stale notice from year {posted_at.year}: {title}")
                continue
            
            # Determine URLs
            attachment_url = None
            if n["attachments"]:
                # Pick the first matching attachment link as main PDF attachment
                attachment_url = n["attachments"][0][1]
            
            # Deduplication key is source_url
            if attachment_url:
                source_url = attachment_url
            elif n["links"]:
                source_url = n["links"][0][1]
            else:
                # Generate unique link if no files are linked
                slug_title = slugify(title)[:60]
                source_url = f"{page_url}#{slug_title}-{n['date']}"

            # Category classification
            category = classify_category(title)
            if category == "notice" and default_category:
                category = default_category

            # Save additional links and metadata
            meta = {
                "original_date": n["date"],
                "all_links": [{"text": txt, "url": href} for txt, href in n["links"]],
                "all_attachments": [{"text": txt, "url": href} for txt, href in n["attachments"]]
            }

            description = f"Notification published by Gauhati University on {n['date']}."

            items.append({
                "title": title,
                "description": description,
                "source_url": source_url,
                "attachment_url": attachment_url,
                "category": category,
                "content_type": category,
                "posted_at": posted_at,
                "tags": ["Gauhati University", "GU", category],
                "metadata": meta,
                "raw_html": f"Date: {n['date']} | Title: {title}"
            })

        return items
