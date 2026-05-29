# normalizer.py - Central Content Normalization Layer

import re
import hashlib
from datetime import datetime, timezone
from typing import Optional, Any
import dateutil.parser

def clean_title(title: str) -> str:
    """
    Standardize title string: strip HTML, clean multiple whitespaces,
    remove trailing brackets/symbols, and trim.
    """
    if not title:
        return ""
    # Strip HTML tags
    cleaned = re.sub(r'<[^>]*>', '', title)
    # Normalize whitespaces/newlines/tabs to a single space
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return cleaned.strip()

def normalize_description(description: str) -> str:
    """
    Clean and normalize description content, removing HTML tags
    and formatting whitespace.
    """
    if not description:
        return ""
    cleaned = re.sub(r'<[^>]*>', '', description)
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return cleaned.strip()

def normalize_date(date_input: Any) -> Optional[datetime]:
    """
    Parse a date input of varying string/datetime formats into a timezone-aware UTC datetime.
    """
    if not date_input:
        return None
        
    if isinstance(date_input, datetime):
        if date_input.tzinfo is None:
            return date_input.replace(tzinfo=timezone.utc)
        return date_input.astimezone(timezone.utc)
        
    date_str = str(date_input).strip()
    # Strip common noise phrases
    date_str = re.sub(r'(?i)posted\s+on\s*:?', '', date_str)
    date_str = re.sub(r'(?i)published\s+on\s*:?', '', date_str)
    date_str = re.sub(r'(?i)date\s*:?', '', date_str)
    date_str = date_str.strip()
    
    if not date_str:
        return None
        
    try:
        dt = dateutil.parser.parse(date_str, fuzzy=True)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
            
        # Year sanity range check
        if 2000 <= dt.year <= 2100:
            return dt
        return None
    except Exception:
        return None

def normalize_category(title: str) -> str:
    """
    Classify a title string into one of the standard platform categories.
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
    elif any(k in title_lower for k in ["scholarship", "scholarships", "fellowship", "award", "stipend", "grant", "aasoni", "nijut"]):
        return "scholarship"
    elif any(k in title_lower for k in ["recruit", "advt", "vacancy", "advertisement", "post of", "recruitment", "appoint"]):
        return "recruitment"
    else:
        return "notice"

def generate_content_hash(title: str, description: str) -> str:
    """
    Generate a SHA256 content hash based on normalized title and description.
    Provides unique signature for deduplication matching between different sources.
    """
    norm_title = clean_title(title).lower()
    norm_desc = normalize_description(description).lower()
    
    # We join clean title and description as the fingerprint base
    hash_base = f"{norm_title}|{norm_desc}"
    return hashlib.sha256(hash_base.encode("utf-8")).hexdigest()
