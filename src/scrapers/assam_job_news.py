import requests
from datetime import datetime, timezone
from typing import List, Dict, Any
from bs4 import BeautifulSoup

from scrapers.base_scraper import BaseScraper
from utils.parser_utils import resolve_url
from utils.normalizer import clean_title, normalize_date, normalize_category

class AssamJobNewsScraper(BaseScraper):
    SOURCE_NAME = "assamJOBnews"
    SOURCE_TYPE = "aggregator"
    BASE_URL = "https://www.assamjobnews.in"
    CATEGORY = "jobs"
    SUPPORTED_CONTENT = ["recruitment", "result", "exam"]
    RELIABILITY_SCORE = 6

    def __init__(self):
        super().__init__(
            name="assam_job_news",
            institution="assamJOBnews",
            source="assamJOBnews"
        )
        self.feed_url = "https://www.assamjobnews.in/feeds/posts/default?alt=json"

    def scrape(self) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        seen = set()

        try:
            self.logger.info(f"Fetching Blogger JSON feed: {self.feed_url}")
            response = self.fetch_url(self.feed_url)
            data = response.json()
            
            feed = data.get("feed", {})
            entries = feed.get("entry", [])
            self.logger.info(f"Parsed {len(entries)} entries from Blogger feed")

            for entry in entries:
                title = clean_title(entry.get("title", {}).get("$t", ""))
                if not title or len(title) < 10 or title in seen:
                    continue

                seen.add(title)

                # Extract post date
                posted_at = None
                pub_date_str = entry.get("published", {}).get("$t")
                if pub_date_str:
                    posted_at = normalize_date(pub_date_str)
                if not posted_at:
                    posted_at = datetime.now(timezone.utc)

                # Get alternate link (public post URL)
                source_url = None
                for link in entry.get("link", []):
                    if link.get("rel") == "alternate":
                        source_url = link.get("href")
                        break

                if not source_url:
                    continue

                # Parse post content to extract a clean description snippet and search for PDF/attachment URLs
                content_html = entry.get("content", {}).get("$t", "")
                description = ""
                attachment_url = None
                
                if content_html:
                    content_soup = BeautifulSoup(content_html, "html.parser")
                    
                    # 1. Clean description snippet (first 300 chars)
                    raw_text = content_soup.get_text(separator=" ").strip()
                    clean_desc = " ".join(raw_text.split())
                    if len(clean_desc) > 300:
                        description = clean_desc[:297] + "..."
                    else:
                        description = clean_desc

                    # 2. Extract PDF or Google Drive attachment if referenced
                    for a in content_soup.find_all("a", href=True):
                        href = a["href"].strip()
                        text = a.get_text(strip=True).lower()
                        
                        # Look for download links, PDF links, or Drive documents
                        if href.lower().endswith(".pdf") or "drive.google.com" in href.lower():
                            attachment_url = href
                            break
                        if any(k in text for k in ["download", "pdf link", "official notification", "click here"]):
                            if "drive.google.com" in href.lower() or ".pdf" in href.lower():
                                attachment_url = href
                                break

                if not description:
                    description = f"Latest recruitment/exam notification: '{title}'. Sourced from assamJOBnews aggregator."

                # Categorization
                category = normalize_category(title)
                if category == "notice":
                    category = "recruitment"  # default to recruitment for aggregator

                # Extract category tags from Blogger terms
                tags = ["assamJOBnews", "Aggregator", "Job", category]
                for term_obj in entry.get("category", []):
                    term = term_obj.get("term")
                    if term and term not in tags:
                        tags.append(term)

                items.append({
                    "title": title,
                    "description": description,
                    "source_url": source_url,
                    "canonical_url": source_url,
                    "attachment_url": attachment_url,
                    "category": category,
                    "content_type": category,
                    "posted_at": posted_at,
                    "tags": tags,
                    "metadata": {
                        "entry_id": entry.get("id", {}).get("$t"),
                        "updated_at": entry.get("updated", {}).get("$t")
                    },
                    "raw_html": content_html[:2000] # Store first 2000 chars of HTML as raw content snapshot
                })

                if len(items) >= 40:
                    break

        except Exception as e:
            self.logger.error(f"Error parsing Blogger feed for assamJOBnews: {e}")

        return items
