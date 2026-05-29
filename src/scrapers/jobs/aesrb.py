from typing import List, Dict, Any
from scrapers.base_scraper import BaseScraper
from utils.parser_utils import parse_date

AESRB_ITEMS = [
    {
        "advt": "AESRB-02/2025 & 03/2025",
        "title": "Assistant Professor (Technical & Non-Technical) — State Engineering Colleges",
        "vacancies": "58",
        "salary": "₹57,700–₹1,82,400",
        "qual": "B.E./B.Tech + M.E./M.Tech First Class",
        "lastDate": "2026-05-08",
        "url": "https://www.aesrb.in",
        "desc": "58 Assistant Professor vacancies in State Engineering Colleges. Apply online at aesrb.in only. Fee: ₹250 Gen / ₹150 OBC / Free SC/ST/PwBD."
    },
    {
        "advt": "AESRB-01/2025",
        "title": "Lecturer & Senior Instructor — Government Polytechnic Institutes",
        "vacancies": "343",
        "salary": "₹30,000–₹1,10,000",
        "qual": "B.E./B.Tech or Master's Degree First Class",
        "lastDate": "2026-09-01",
        "url": "https://www.aesrb.in",
        "desc": "343 Lecturer and Senior Instructor vacancies across Technical and Non-Technical disciplines in polytechnics. Apply online at aesrb.in."
    }
]

class AESRBScraper(BaseScraper):
    def __init__(self):
        super().__init__(
            name="aesrb",
            institution="Assam Engineering Service Recruitment Board",
            source="AESRB Official"
        )
        self.website_url = "https://www.aesrb.in"

    def scrape(self) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []

        self.logger.info("Parsing AESRB notices (JS React SPA - using structured data)")
        for idx, n in enumerate(AESRB_ITEMS):
            posted_at = parse_date("2026-04-15")  # mock published date
            items.append({
                "title": n["title"],
                "description": n["desc"],
                "source_url": f"https://www.aesrb.in/recruitment-{idx}",
                "category": "recruitment",
                "content_type": "recruitment",
                "posted_at": posted_at,
                "tags": ["AESRB", "Engineering Colleges", "Recruitment"],
                "metadata": {
                    "advt_no": n["advt"],
                    "vacancies": n["vacancies"],
                    "salary": n["salary"],
                    "qualification": n["qual"],
                    "last_date": n["lastDate"],
                    "apply_url": n["url"]
                },
                "raw_html": f"AESRB Entry: {n['title']} (Advt: {n['advt']})"
            })

        return items
