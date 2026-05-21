import re
from typing import List, Dict, Any
from bs4 import BeautifulSoup

from scrapers.base_scraper import BaseScraper
from utils.parser_utils import clean_text, parse_date, classify_category

class AssamCareerScraper(BaseScraper):
    def __init__(self):
        super().__init__(
            name="assam_career",
            institution="Assam Career",
            source="AssamCareer.com"
        )
        self.pages = [
            "https://www.assamcareer.com/",
            "https://www.assamcareer.com/search/label/Banking",
            "https://www.assamcareer.com/search/label/Govt%20Job",
            "https://www.assamcareer.com/search/label/Private%20Job",
            "https://www.assamcareer.com/search/label/Teaching%20Job",
            "https://www.assamcareer.com/search/label/Defence",
            "https://www.assamcareer.com/search/label/Police",
            "https://www.assamcareer.com/search/label/Railway",
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
                self.logger.info(f"Scraping AssamCareer page: {page_url}")
                response = self.fetch_url(page_url)
                soup = BeautifulSoup(response.text, "html.parser")

                posts = (
                    soup.select(".post-title") or
                    soup.select("h3.post-title") or
                    soup.select("h2.post-title") or
                    soup.select(".entry-title") or
                    soup.select("h3 a") or
                    soup.select("h2 a")
                )

                for el in posts[:15]:
                    a = el if el.name == "a" else el.find("a")
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

                    # Extract excerpt
                    parent = el.parent or el
                    excerpt_el = (
                        parent.find("div", class_="post-body") or
                        parent.find("div", class_="entry-content") or
                        parent.find("p")
                    )
                    excerpt = clean_text(excerpt_el.get_text())[:300] if excerpt_el else ""

                    # Extract date string
                    date_match = re.search(
                        r'(\d{1,2}\s+[A-Za-z]+,?\s+\d{4}|\d{2}[-/\.]\d{2}[-/\.]\d{4})', 
                        excerpt + " " + title
                    )
                    posted_at = None
                    if date_match:
                        posted_at = parse_date(date_match.group(1))

                    # Fallback to classify category
                    category = classify_category(title)
                    # For jobs portal, default category is recruitment
                    if category == "notice":
                        category = "recruitment"

                    items.append({
                        "title": title,
                        "description": excerpt or f"{title}. Sourced from AssamCareer.com.",
                        "source_url": href,
                        "category": category,
                        "content_type": category,
                        "posted_at": posted_at,
                        "tags": ["AssamCareer", "Job", category],
                        "metadata": {
                            "excerpt": excerpt,
                            "original_source": "AssamCareer.com"
                        },
                        "raw_html": f"Title: {title} | Link: {href}"
                    })

            except Exception as e:
                self.logger.error(f"Error scraping {page_url}: {e}")

        return items
