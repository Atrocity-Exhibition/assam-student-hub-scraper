import re
from typing import List, Dict, Any
from bs4 import BeautifulSoup

from scrapers.base_scraper import BaseScraper
from utils.parser_utils import clean_text, parse_date, classify_category

class DailyAssamJobScraper(BaseScraper):
    def __init__(self):
        super().__init__(
            name="daily_assam_job",
            institution="Daily Assam Job",
            source="DailyAssamJob.in"
        )
        self.pages = [
            "https://www.dailyassamjob.in/",
            "https://www.dailyassamjob.in/search/label/Assam%20Govt%20Job",
            "https://www.dailyassamjob.in/search/label/Private%20Job",
            "https://www.dailyassamjob.in/search/label/Bank%20Job",
            "https://www.dailyassamjob.in/search/label/Railway%20Job",
            "https://www.dailyassamjob.in/search/label/Defence%20Job",
            "https://www.dailyassamjob.in/search/label/Teaching%20Job",
            "https://www.dailyassamjob.in/search/label/Guwahati%20Job",
        ]
        self.job_kw = [
            "recruitment", "vacancy", "post", "hiring", "notification", "advt",
            "assistant", "officer", "engineer", "teacher", "professor", "constable",
            "inspector", "driver", "nurse", "doctor", "clerk", "staff", "manager", "loco"
        ]

    def scrape(self) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        seen = set()

        for page_url in self.pages:
            try:
                self.logger.info(f"Scraping DailyAssamJob page: {page_url}")
                response = self.fetch_url(page_url)
                soup = BeautifulSoup(response.text, "html.parser")

                posts = (
                    soup.select(".post-title") or
                    soup.select("h3.post-title") or
                    soup.select("h2.post-title") or
                    soup.select(".entry-title") or
                    soup.select("h3 a") or
                    soup.select("article")
                )

                for art in posts[:20]:
                    a = art if art.name == "a" else (art.find("a") or art.select_one("a"))
                    if not a:
                        continue
                    title = clean_text(a.get_text())
                    href = a.get("href", "")
                    if not title or len(title) < 10 or title in seen:
                        continue
                    
                    # Relevance filter
                    if not any(k in title.lower() for k in self.job_kw):
                        continue
                    
                    seen.add(title)

                    excerpt_el = art.select_one("p") or art.select_one(".entry-summary")
                    excerpt = clean_text(excerpt_el.get_text())[:280] if excerpt_el else ""

                    date_match = re.search(
                        r'(\d{1,2}\s+[A-Za-z]+,?\s+\d{4}|\d{2}[-/\.]\d{2}[-/\.]\d{4})', 
                        excerpt + " " + title
                    )
                    posted_at = None
                    if date_match:
                        posted_at = parse_date(date_match.group(1))

                    category = classify_category(title)
                    if category == "notice":
                        category = "recruitment"

                    items.append({
                        "title": title,
                        "description": excerpt or f"{title}. Sourced from DailyAssamJob.in.",
                        "source_url": href,
                        "category": category,
                        "content_type": category,
                        "posted_at": posted_at,
                        "tags": ["DailyAssamJob", "Job", category],
                        "metadata": {
                            "excerpt": excerpt,
                            "original_source": "DailyAssamJob.in"
                        },
                        "raw_html": f"Title: {title} | Link: {href}"
                    })

            except Exception as e:
                self.logger.error(f"Error scraping {page_url}: {e}")

        return items
