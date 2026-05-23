import time
import random
import requests
from datetime import datetime, timezone
from typing import List, Dict, Any

from scrapers.base_scraper import BaseScraper
from utils.parser_utils import resolve_url
from utils.normalizer import clean_title, normalize_date, normalize_category

class AWUScraper(BaseScraper):
    SOURCE_NAME = "Assam Women's University"
    SOURCE_TYPE = "university"
    BASE_URL = "https://awu.ac.in"
    CATEGORY = "mixed"
    SUPPORTED_CONTENT = ["recruitment", "result", "exam", "admission", "scholarship", "notice"]
    RELIABILITY_SCORE = 10

    def __init__(self):
        super().__init__(
            name="awu",
            institution="Assam Women's University",
            source="AWU"
        )
        self.api_url = "https://admission.awu.ac.in/api/public-notifications"
        # Map original API types to standard category terms
        self.types = [
            ("admission", "admission"),
            ("examination", "exam"),
            ("results", "result"),
            ("recruitment", "recruitment"),
            ("scholarships", "scholarship"),
            ("miscellaneous", "notice")
        ]

    def scrape(self) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        seen = set()

        for type_val, default_cat in self.types:
            try:
                self.logger.info(f"Querying AWU AJAX API for type: '{type_val}'")

                # Polite crawling rate limits
                if self.jitter:
                    actual_delay = random.uniform(self.delay_seconds * 0.5, self.delay_seconds * 1.5)
                else:
                    actual_delay = self.delay_seconds
                time.sleep(actual_delay)

                payload = {
                    "type": type_val,
                    "year": "",
                    "per_page": 30,
                    "page": 1
                }

                # POST request to fetch dynamic API notifications list
                res = requests.post(
                    self.api_url,
                    data=payload,
                    headers=self.headers,
                    verify=False,
                    timeout=self.timeout
                )
                res.raise_for_status()

                data = res.json()
                notifications = data.get("notifications", {}).get("data", [])
                self.logger.info(f"Retrieved {len(notifications)} records for type '{type_val}'")

                for n in notifications:
                    title = clean_title(n.get("title", ""))
                    if not title or len(title) < 10 or title in seen:
                        continue

                    seen.add(title)

                    # Normalize publish_date
                    posted_at = None
                    pub_date = n.get("publish_date")
                    if pub_date:
                        posted_at = normalize_date(pub_date)
                    if not posted_at:
                        posted_at = datetime.now(timezone.utc)

                    # Attachment URL
                    attachment_url = None
                    attachment_rel = n.get("attachment")
                    if attachment_rel:
                        # Resolves against API server base: https://admission.awu.ac.in/
                        attachment_url = resolve_url("https://admission.awu.ac.in/", attachment_rel)

                    # Categorize notice
                    category = normalize_category(title)
                    if category == "notice":
                        category = default_cat

                    items.append({
                        "title": title,
                        "description": f"Official notice from Assam Women's University: '{title}'. Sourced from AWU Portal.",
                        "source_url": "https://awu.ac.in/notifications.html",
                        "canonical_url": "https://awu.ac.in/notifications.html",
                        "attachment_url": attachment_url,
                        "category": category,
                        "content_type": category,
                        "posted_at": posted_at,
                        "tags": ["AWU", "University", "Jorhat", category],
                        "metadata": {
                            "original_type": type_val,
                            "publish_date_raw": pub_date,
                            "api_id": n.get("id")
                        },
                        "raw_html": str(n)
                    })

            except Exception as e:
                self.logger.error(f"Error querying AWU API for type '{type_val}': {e}")

        return items
