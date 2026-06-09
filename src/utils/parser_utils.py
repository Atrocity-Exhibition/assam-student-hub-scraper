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
        # Fuzzy parsing handles different formats automatically. Prioritize Day-first for Indian sites (DD-MM-YYYY)
        dt = dateutil.parser.parse(cleaned, fuzzy=True, dayfirst=True)
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

