import json
from datetime import datetime
from typing import List, Dict, Any, Optional
import requests

from scrapers.base_scraper import BaseScraper
from utils.parser_utils import parse_date, classify_category
from utils.field_extractor import extract_fields_for_category

class DibrugarhScraper(BaseScraper):
    def __init__(self, limit: int = 30):
        """
        Initialize the Dibrugarh University Scraper.
        :param limit: Number of posts to fetch from the public API.
        """
        super().__init__(
            name="dibrugarh",
            institution="Dibrugarh University",
            source="Dibrugarh University"
        )
        self.limit = limit
        self.api_url = f"https://lionfish-app-3a378.ondigitalocean.app/api/website/public/posts?limit={limit}"
        # Set headers specifically needed by Dibrugarh's API to bypass CORS/Origin protections
        self.headers.update({
            "Origin": "https://dibru.ac.in",
            "Referer": "https://dibru.ac.in/",
            "Accept": "application/json",
            "Content-Type": "application/json"
        })

    def scrape(self) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []

        try:
            self.logger.info(f"Fetching Dibrugarh University JSON API: {self.api_url}")
            response = self.fetch_url(self.api_url)
            
            if response.status_code != 200:
                self.logger.error(f"Dibrugarh API returned status {response.status_code}: {response.text}")
                return results

            payload = response.json()
            posts = payload.get("data", [])
            self.logger.info(f"Fetched {len(posts)} posts from Dibrugarh University API.")

            for post in posts:
                try:
                    title = post.get("title", "").strip()
                    slug = post.get("slug", "").strip()
                    if not title or not slug:
                        continue

                    # Construct canonical detail page link
                    source_url = f"https://dibru.ac.in/posts/{slug}"
                    
                    # Parse published date
                    published_date_str = post.get("published_date")
                    posted_at = parse_date(published_date_str) if published_date_str else None

                    # Category resolution
                    api_categories = post.get("categories", [])
                    category_slugs = [c.get("slug", "").lower() for c in api_categories if c.get("slug")]
                    
                    category = "notice"
                    if "results" in category_slugs:
                        category = "result"
                    elif "admissions" in category_slugs:
                        category = "admission"
                    elif "careers" in category_slugs:
                        category = "recruitment"
                    else:
                        # Fall back to text classification
                        category = classify_category(title)

                    # Parse block content JSON to find attachments
                    content_str = post.get("content", "[]")
                    attachment_url = None
                    all_attachments = []
                    all_links = []

                    try:
                        # Dibrugarh editor content is stringified JSON
                        blocks = json.loads(content_str)
                        if isinstance(blocks, list):
                            for block in blocks:
                                b_type = block.get("type")
                                b_props = block.get("props", {})
                                
                                # PDF block
                                if b_type == "pdf" and b_props.get("url"):
                                    pdf_url = b_props["url"]
                                    pdf_name = b_props.get("name", "Attachment")
                                    all_attachments.append({"text": pdf_name, "url": pdf_url})
                                
                                # Process inline links inside paragraphs or headings
                                b_content = block.get("content", [])
                                if isinstance(b_content, list):
                                    for item in b_content:
                                        if isinstance(item, dict) and item.get("type") == "link":
                                            link_url = item.get("href")
                                            link_txt = ""
                                            link_sub = item.get("content", [])
                                            if isinstance(link_sub, list) and link_sub:
                                                link_txt = link_sub[0].get("text", "Link")
                                            
                                            if link_url:
                                                if ".pdf" in link_url.lower():
                                                    all_attachments.append({"text": link_txt, "url": link_url})
                                                else:
                                                    all_links.append({"text": link_txt, "url": link_url})
                    except Exception as je:
                        self.logger.warning(f"Failed to parse content block JSON for post {slug}: {je}")

                    # Select primary attachment URL
                    if all_attachments:
                        attachment_url = all_attachments[0]["url"]

                    # Fallback description
                    description = post.get("excerpt") or f"Notification published by Dibrugarh University on {posted_at.strftime('%Y-%m-%d') if posted_at else 'recent date'}."

                    metadata = {
                        "post_id": post.get("id"),
                        "slug": slug,
                        "all_attachments": all_attachments,
                        "all_links": all_links,
                        "archive_date": post.get("archive_date")
                    }
                    extracted_meta = extract_fields_for_category(category, title, description)
                    metadata.update(extracted_meta)

                    results.append({
                        "title": title,
                        "description": description,
                        "source_url": source_url,
                        "attachment_url": attachment_url,
                        "category": category,
                        "content_type": category,
                        "posted_at": posted_at,
                        "tags": ["Dibrugarh University", "DU", category],
                        "metadata": metadata,
                        "raw_html": content_str[:2000] # Save raw blocks snippet
                    })

                except Exception as pe:
                    self.logger.error(f"Error parsing post record: {pe}")

        except Exception as e:
            self.logger.error(f"Error executing Dibrugarh Scraper: {e}")

        return results
