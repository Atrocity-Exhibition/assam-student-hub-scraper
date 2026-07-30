import re
from typing import List, Dict, Any
from bs4 import BeautifulSoup

from scrapers.base_scraper import BaseScraper
from utils.parser_utils import clean_text, parse_date, classify_category
from utils.normalizer import clean_title, normalize_date, normalize_category

class AssamCareerScraper(BaseScraper):
    def __init__(self):
        super().__init__(
            name="assam_career",
            institution="Assam Career",
            source="AssamCareer.com",
            institution_slug="assam-career"
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
            "inspector", "driver", "nurse", "doctor", "clerk", "staff", "manager", "loco",
            "scheme", "admit card", "result"
        ]

    def _html_to_markdown(self, element) -> str:
        """
        Convert BeautifulSoup post body into structured Markdown text
        preserving headings, lists, tables, and quote blocks.
        """
        if not element:
            return ""
        
        # Parse copy to safely decompose unwanted tags
        element_copy = BeautifulSoup(str(element), "html.parser")
        for noise in element_copy.select("script, style, ins, .adsbygoogle, .simplesharebuttons, .inline-ad, iframe, .post-share-buttons"):
            noise.decompose()
            
        markdown_lines = []
        
        for child in element_copy.children:
            if child.name is None:
                text = child.string or ""
                if text.strip():
                    markdown_lines.append(text.strip())
                continue
                
            if child.name in ["h1", "h2"]:
                htext = clean_text(child.get_text())
                if htext:
                    markdown_lines.append(f"\n## {htext}\n")
            elif child.name in ["h3", "h4", "h5", "h6"]:
                htext = clean_text(child.get_text())
                if htext:
                    markdown_lines.append(f"\n### {htext}\n")
            elif child.name == "p":
                ptext = clean_text(child.get_text())
                if ptext:
                    markdown_lines.append(f"\n{ptext}\n")
            elif child.name in ["ul", "ol"]:
                for li in child.find_all("li", recursive=False):
                    litext = clean_text(li.get_text())
                    if litext:
                        markdown_lines.append(f"- {litext}")
                markdown_lines.append("")
            elif child.name == "table":
                rows = child.find_all("tr")
                if not rows:
                    continue
                table_md = []
                for idx, tr in enumerate(rows):
                    cols = [clean_text(c.get_text()) for c in tr.find_all(["td", "th"])]
                    if not cols or not any(cols):
                        continue
                    row_str = "| " + " | ".join(cols) + " |"
                    table_md.append(row_str)
                    if idx == 0:
                        separators = ["---"] * len(cols)
                        table_md.append("| " + " | ".join(separators) + " |")
                if table_md:
                    markdown_lines.append("\n" + "\n".join(table_md) + "\n")
            elif child.name == "blockquote":
                btext = clean_text(child.get_text())
                if btext:
                    markdown_lines.append(f"> {btext}\n")
            else:
                text = clean_text(child.get_text())
                if text and len(text) > 10:
                    markdown_lines.append(text)
                    
        result = "\n".join(markdown_lines)
        result = re.sub(r"\n{3,}", "\n\n", result)
        return result.strip()

    def _scrape_detail_page(self, href: str) -> Dict[str, Any]:
        """
        Fetch individual post page and extract full details, markdown content,
        tables metadata, apply_url, and attachment_url.
        """
        try:
            self.logger.info(f"Fetching AssamCareer detail page: {href}")
            response = self.fetch_url(href)
            dsoup = BeautifulSoup(response.text, "html.parser")
            body = dsoup.select_one(".post-body") or dsoup.select_one(".entry-content") or dsoup.select_one("article")
            if not body:
                return {}

            body_copy = BeautifulSoup(str(body), "html.parser")
            for noise in body_copy.select("script, style, ins, .adsbygoogle, .simplesharebuttons, .inline-ad, iframe, .post-share-buttons"):
                noise.decompose()

            extracted_meta = {}
            attachment_url = None
            apply_url = None

            tables = body.find_all("table")
            for table in tables:
                rows = table.find_all("tr")
                for row in rows:
                    cols = [clean_text(c.get_text()) for c in row.find_all(["td", "th"])]
                    if len(cols) == 2:
                        k, v = cols[0].lower(), cols[1]
                        if not v or v.lower() in ["click here", "n/a", "nil"]:
                            pass
                        elif "vacanc" in k or "no of post" in k or "number of post" in k or "name of post" in k:
                            if "vacancies" not in extracted_meta:
                                extracted_meta["vacancies"] = v
                        elif "salary" in k or "pay" in k or "stipend" in k or "scale of pay" in k:
                            if "salary" not in extracted_meta:
                                extracted_meta["salary"] = v
                        elif "qualific" in k or "eligib" in k:
                            if "qualification" not in extracted_meta:
                                extracted_meta["qualification"] = v
                        elif "last date" in k or "apply by" in k or "deadline" in k:
                            if "last_date" not in extracted_meta:
                                extracted_meta["last_date"] = v
                        elif "advt" in k or "notification no" in k:
                            if "advt_no" not in extracted_meta:
                                extracted_meta["advt_no"] = v
                        elif "age limit" in k or "age" in k:
                            if "age_limit" not in extracted_meta:
                                extracted_meta["age_limit"] = v

                    # Check links inside table row
                    for a in row.find_all("a", href=True):
                        a_href = a["href"].strip()
                        a_text = clean_text(a.get_text()).lower()
                        row_text = clean_text(row.get_text()).lower()

                        if ("official notification" in row_text or "advertisement" in row_text or "pdf" in a_text or "guidelines" in row_text) and not attachment_url:
                            if ".pdf" in a_href.lower() or "drive.google.com" in a_href.lower() or "http" in a_href:
                                attachment_url = a_href
                        if ("online application" in row_text or "apply online" in row_text or "register" in a_text or "login" in a_text) and not apply_url:
                            if "assamcareer.com" not in a_href and "whatsapp" not in a_href:
                                apply_url = a_href

            # Fallback scan for attachment and apply URLs in body
            if not attachment_url or not apply_url:
                for a in body.find_all("a", href=True):
                    a_href = a["href"].strip()
                    a_text = clean_text(a.get_text()).lower()
                    if not attachment_url and (".pdf" in a_href.lower() or "drive.google.com" in a_href.lower()):
                        attachment_url = a_href
                    if not apply_url and ("apply" in a_text or "online form" in a_text or "registration" in a_text) and "assamcareer" not in a_href and "whatsapp" not in a_href:
                        apply_url = a_href

            if apply_url:
                extracted_meta["apply_url"] = apply_url

            markdown_desc = self._html_to_markdown(body)
            raw_html_clean = str(body_copy)

            date_match = re.search(
                r'(\d{1,2}\s+[A-Za-z]+,?\s+\d{4}|\d{2}[-/\.]\d{2}[-/\.]\d{4})',
                clean_text(body.get_text()[:600])
            )
            posted_at = parse_date(date_match.group(1)) if date_match else None

            return {
                "description": markdown_desc,
                "metadata": extracted_meta,
                "attachment_url": attachment_url,
                "raw_html": raw_html_clean,
                "posted_at": posted_at
            }
        except Exception as e:
            self.logger.warning(f"Error scraping detail page {href}: {e}")
            return {}

    def scrape(self) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        seen_titles = set()
        seen_urls = set()

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
                    href = a.get("href", "").strip()
                    if not title or len(title) < 10 or title in seen_titles or href in seen_urls:
                        continue
                    
                    # Relevance filter
                    if not any(k in title.lower() for k in self.job_kw):
                        continue
                    
                    seen_titles.add(title)
                    seen_urls.add(href)

                    # Extract listing excerpt
                    parent = el.parent or el
                    excerpt_el = (
                        parent.find("div", class_="post-body") or
                        parent.find("div", class_="entry-content") or
                        parent.find("p")
                    )
                    excerpt = clean_text(excerpt_el.get_text())[:280] if excerpt_el else ""

                    # Fetch full detail page content
                    detail = self._scrape_detail_page(href)

                    # Default date string from excerpt or detail
                    posted_at = detail.get("posted_at")
                    if not posted_at:
                        date_match = re.search(
                            r'(\d{1,2}\s+[A-Za-z]+,?\s+\d{4}|\d{2}[-/\.]\d{2}[-/\.]\d{4})', 
                            excerpt + " " + title
                        )
                        if date_match:
                            posted_at = parse_date(date_match.group(1))

                    category = classify_category(title)
                    if category == "notice":
                        category = "recruitment"

                    description = detail.get("description") or excerpt or f"{title}. Sourced from AssamCareer.com."

                    metadata = {
                        "excerpt": excerpt,
                        "original_source": "AssamCareer.com",
                        **(detail.get("metadata") or {})
                    }

                    items.append({
                        "title": title,
                        "description": description,
                        "source_url": href,
                        "canonical_url": href,
                        "attachment_url": detail.get("attachment_url"),
                        "category": category,
                        "content_type": category,
                        "posted_at": posted_at,
                        "tags": ["AssamCareer", "Job", category],
                        "metadata": metadata,
                        "raw_html": detail.get("raw_html") or f"Title: {title} | Link: {href}"
                    })

                    # Cap to avoid excessive execution time if needed
                    if len(items) >= 40:
                        break

            except Exception as e:
                self.logger.error(f"Error scraping {page_url}: {e}")

        return items

