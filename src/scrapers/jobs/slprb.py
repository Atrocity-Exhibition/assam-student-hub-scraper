import copy
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
import requests

from scrapers.base_scraper import BaseScraper
from utils.parser_utils import resolve_url, clean_text, parse_date, classify_category
from utils.field_extractor import extract_fields_for_category

class SLPRBScraper(BaseScraper):
    def __init__(self):
        """
        Initialize the State Level Police Recruitment Board (SLPRB) Scraper.
        """
        super().__init__("slprb", "State Level Police Recruitment Board", "SLPRB")
        self.base_url = "https://slprbassam.in"

    def scrape(self) -> List[Dict[str, Any]]:
        """
        Scrapes recruitment notices and advertisements from the SLPRB homepage.
        """
        results: List[Dict[str, Any]] = []
        try:
            response = self.fetch_url(self.base_url)
            results = self._parse_homepage(response.text)
            self.logger.info(f"Successfully scraped {len(results)} items from SLPRB.")
        except Exception as e:
            self.logger.error(f"Unexpected error scraping SLPRB: {e}")
            
        return results

    def _parse_homepage(self, html: str) -> List[Dict[str, Any]]:
        """
        Parses the recruitment board table.
        Columns: ['Update Date', 'Advertisement No', 'Description']
        """
        items: List[Dict[str, Any]] = []
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        if not table:
            self.logger.warning("No notices table found on SLPRB homepage.")
            return items

        rows = table.find_all("tr")
        for idx, row in enumerate(rows):
            cells = row.find_all(["td", "th"])
            if not cells or len(cells) < 3:
                continue

            cell_texts = [clean_text(c.get_text()) for c in cells]
            
            # Skip header row: ['Update Date', 'Advertisement No', 'Description']
            if "Update Date" in cell_texts[0] or "Advertisement No" in cell_texts[1] or "Description" in cell_texts[2]:
                self.logger.debug(f"Skipping header row at index {idx}")
                continue

            date_cell = cells[0]
            advt_cell = cells[1]
            desc_cell = cells[2]

            # 1. Clean and parse date
            date_raw = date_cell.get_text(strip=True)
            # Remove badges like "| new", "| new new"
            if "|" in date_raw:
                date_str = date_raw.split("|")[0].strip()
            else:
                date_str = date_raw.strip()
            posted_at = parse_date(date_str)

            # 2. Extract Advt/Reference number
            advt_no = clean_text(advt_cell.get_text())

            # 3. Find links inside the description cell
            links = desc_cell.find_all("a", href=True)
            if not links:
                self.logger.debug(f"No document links found in row {idx}: {cell_texts[2][:50]}...")
                continue

            # 4. Extract description without the link text at the end (e.g. decomposing <a> tags)
            desc_cell_copy = copy.copy(desc_cell)
            for link_tag in desc_cell_copy.find_all("a"):
                link_tag.decompose()
            clean_desc = clean_text(desc_cell_copy.get_text())

            # Process each link in this row as a notice item
            for a_idx, a_tag in enumerate(links):
                href = a_tag["href"].strip()
                if not href or href.startswith("javascript:"):
                    continue

                pdf_url = resolve_url(self.base_url, href)
                link_label = clean_text(a_tag.get_text())

                # Build clean title
                title = clean_desc
                if not title:
                    title = f"{link_label} for Advertisement No: {advt_no}" if advt_no else f"SLPRB Update - {link_label}"
                
                # Append advertisement number to title if not already present
                if advt_no and advt_no.lower() not in title.lower():
                    title = f"{title} (Advt No. {advt_no})"

                category = classify_category(title)
                
                # Format tags and deduplicate
                tags = ["SLPRB", "Assam Police", "recruitment"]
                if advt_no:
                    tags.append(advt_no)
                if category not in tags:
                    tags.append(category)
                
                # Clean tags list
                tags = sorted(list(set(clean_text(tag) for tag in tags if tag)))

                # Formulate metadata
                meta = {
                    "advertisement_no": advt_no,
                    "link_label": link_label,
                    "update_date_raw": date_raw,
                    "row_index": idx,
                    "link_index": a_idx
                }
                extracted_meta = extract_fields_for_category(category, title, description)
                meta.update(extracted_meta)

                description = f"SLPRB Recruitment Notice. Reference No: {advt_no}." if advt_no else "SLPRB Recruitment Notice."

                items.append({
                    "title": title,
                    "description": description,
                    "source_url": pdf_url,
                    "attachment_url": pdf_url,
                    "category": category,
                    "content_type": category,
                    "posted_at": posted_at,
                    "tags": tags,
                    "raw_html": str(row),
                    "metadata": meta
                })

        return items
