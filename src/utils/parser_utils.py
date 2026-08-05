import re
import urllib.parse
from datetime import datetime, timezone
from typing import Optional
import dateutil.parser

def clean_text(text: str) -> str:
    """
    Remove HTML formatting characters, normalize consecutive whitespaces,
    and strip leading/trailing spaces.
    """
    if not text:
        return ""
    # Strip HTML tags just in case
    text = re.sub(r'<[^>]*>', '', text)
    # Replace multiple whitespaces/newlines/tabs with a single space
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def resolve_url(base_url: str, relative_url: str) -> str:
    """
    Safely resolve a relative URL using the base URL.
    Returns the resolved absolute URL.
    """
    if not relative_url:
        return ""
    relative_url = relative_url.strip()
    return urllib.parse.urljoin(base_url, relative_url)

def parse_date(date_str: str) -> Optional[datetime]:
    """
    Safely parse date strings of various formats into a timezone-aware UTC datetime.
    Strips noise like 'Posted on :' or 'Date: ' prior to parsing.
    Returns None if parsing fails.
    """
    if not date_str:
        return None
    
    # Strip common noise phrases
    cleaned = re.sub(r'(?i)posted\s+on\s*:?', '', date_str)
    cleaned = re.sub(r'(?i)published\s+on\s*:?', '', cleaned)
    cleaned = re.sub(r'(?i)date\s*:?', '', cleaned)
    cleaned = cleaned.strip()
    
    if not cleaned:
        return None
        
    try:
        # Check if year-first ISO format (e.g. YYYY-MM-DD or YYYY/MM/DD)
        year_first = False
        if re.match(r'^\s*\d{4}[-/.]\d{1,2}[-/.]\d{1,2}', cleaned):
            year_first = True
            
        # Prioritize Day-first for Indian sites (DD-MM-YYYY) unless it's a year-first format
        dt = dateutil.parser.parse(cleaned, fuzzy=True, dayfirst=not year_first)
        # Force timezone-aware UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
            
        # sanity check: ensure year is reasonable
        if 2000 <= dt.year <= 2100:
            return dt
        return None
    except Exception:
        return None

def classify_category(title: str) -> str:
    """
    Classify a notice title into one of the standard platform categories:
    - recruitment (jobs)
    - result (results/marks)
    - exam (routines/schedules/interviews)
    - admission (admissions)
    - scholarship (scholarships)
    - notice (general notifications)
    """
    if not title:
        return "notice"
        
    title_lower = title.lower()
    
    if any(k in title_lower for k in ["result", "marks", "qualified", "selected candidates", "recommendation list", "results", "selection list"]):
        return "result"
    elif any(k in title_lower for k in ["exam", "routine", "schedule", "viva-voce", "interview", "written test", "admit card", "screening test", "viva"]):
        return "exam"
    elif any(k in title_lower for k in ["admission", "admissions", "intake", "enrolment"]):
        return "admission"
    elif any(k in title_lower for k in ["scholarship", "scholarships", "fellowship", "award"]):
        return "scholarship"
    elif any(k in title_lower for k in ["recruit", "advt", "vacancy", "advertisement", "post of", "recruitment", "appoint"]):
        return "recruitment"
    else:
        return "notice"

def convert_node_to_markdown(node) -> str:
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    
    name = node.name.lower() if node.name else ""

    # Noise removal
    if name in ["script", "style", "ins", "iframe", "meta", "link"]:
        return ""
    
    classes = node.get("class", [])
    if isinstance(classes, list):
        class_str = " ".join(classes).lower()
    else:
        class_str = str(classes).lower()
        
    if any(k in class_str for k in ["group-card", "whatsapp", "telegram", "adsbygoogle", "simplesharebuttons", "post-share"]):
        return ""

    # Inline formatting
    if name in ["b", "strong"]:
        inner = "".join(convert_node_to_markdown(c) for c in node.children).strip()
        return f" **{inner}** " if inner else ""
    elif name in ["i", "em"]:
        inner = "".join(convert_node_to_markdown(c) for c in node.children).strip()
        return f" *{inner}* " if inner else ""
    elif name == "a":
        inner = "".join(convert_node_to_markdown(c) for c in node.children).strip()
        href = node.get("href", "").strip()
        if not inner or not href:
            return inner
        if any(k in inner.lower() or k in href.lower() for k in ["whatsapp", "telegram", "instagram", "follow us"]):
            return ""
        return f" [{inner}]({href}) "
    elif name == "br":
        return "\n"
    elif name in ["h1", "h2"]:
        inner = clean_text(node.get_text())
        return f"\n\n## {inner}\n\n" if inner else ""
    elif name in ["h3", "h4", "h5", "h6"]:
        inner = clean_text(node.get_text())
        return f"\n\n### {inner}\n\n" if inner else ""
    elif name == "p":
        inner = "".join(convert_node_to_markdown(c) for c in node.children).strip()
        return f"\n\n{inner}\n\n" if inner else ""
    elif name == "div":
        inner = "".join(convert_node_to_markdown(c) for c in node.children).strip()
        return f"\n\n{inner}\n\n" if inner else ""
    elif name in ["ul", "ol"]:
        items = []
        for li in node.find_all("li", recursive=False):
            litext = "".join(convert_node_to_markdown(c) for c in li.children).strip()
            if litext:
                items.append(f"- {litext}")
        return "\n\n" + "\n".join(items) + "\n\n"
    elif name == "table":
        rows = node.find_all("tr")
        if not rows:
            return ""
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
        return "\n\n" + "\n".join(table_md) + "\n\n"
    else:
        return "".join(convert_node_to_markdown(c) for c in node.children)

def html_to_clean_markdown(body) -> str:
    """
    Recursively parse HTML post container into clean, well-formatted Markdown
    preserving headings, bold fields, paragraphs, bullet points, tables, and links while
    stripping unwanted promotional noise and social banners.
    """
    if not body:
        return ""
    
    from bs4 import BeautifulSoup
    body_copy = BeautifulSoup(str(body), "html.parser")
    for noise in body_copy.select("script, style, ins, iframe, meta, link, .group-card, .whatsapp-card, .telegram-card, .adsbygoogle, .simplesharebuttons, .post-share-buttons"):
        noise.decompose()
        
    md = convert_node_to_markdown(body_copy)
    
    lines = [line.strip() for line in md.split("\n")]
    result_lines = []
    prev_empty = False
    
    for line in lines:
        if not line:
            if not prev_empty:
                result_lines.append("")
                prev_empty = True
        else:
            line_clean = re.sub(r"[ \t]+", " ", line)
            if any(k in line_clean.lower() for k in ["join whatsapp channel", "follow us telegram", "telegram channel join"]):
                continue
            result_lines.append(line_clean)
            prev_empty = False
            
    return "\n".join(result_lines).strip()


