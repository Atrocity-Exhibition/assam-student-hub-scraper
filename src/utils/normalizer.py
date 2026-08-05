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
    Clean and normalize description content while preserving Markdown formatting and line breaks.
    """
    if not description:
        return ""
    
    # Replace carriage returns
    text = description.replace("\r\n", "\n").replace("\r", "\n")
    
    # Strip HTML tags if raw HTML is passed, preserving paragraph break structure
    if "<" in text and ">" in text:
        text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'</p>', '\n\n', text, flags=re.IGNORECASE)
        text = re.sub(r'</div>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<[^>]*>', '', text)
    
    # Normalize spaces per line while preserving linebreaks
    lines = [re.sub(r'[ \t]+', ' ', line).strip() for line in text.split('\n')]
    
    # Collapse 3+ consecutive newlines to maximum 2 newlines
    result_lines = []
    prev_empty = False
    for line in lines:
        if not line:
            if not prev_empty:
                result_lines.append("")
                prev_empty = True
        else:
            result_lines.append(line)
            prev_empty = False
            
    return "\n".join(result_lines).strip()

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

def classify_filter_metadata(title: str, description: str, metadata: dict) -> dict:
    """
    Classifies a notice into normalized enums for education_level, salary_range, and experience_level.
    """
    text = (title + " " + description).lower()
    
    # Initialize fields inside metadata if not already present
    edu = metadata.get("education_level")
    sal = metadata.get("salary_range")
    exp = metadata.get("experience_level")
    
    # 1. Experience Level Classification
    if not exp:
        exp_match = re.search(r'(\d+)\s*-\s*(\d+)\s*years?\s+exp', text) or \
                    re.search(r'(\d+)\s*\+\s*years?\s+exp', text) or \
                    re.search(r'exp(?:erience)?\s*(?:of|required)?\s*(\d+)\s*years?', text)
        
        fresher_kws = ["fresher", "no experience", "entry level", "training period", "apprentice", "internship"]
        
        if any(k in text for k in fresher_kws):
            exp = "fresher"
        elif exp_match:
            try:
                years = int(exp_match.group(1))
                if years >= 5:
                    exp = "5_plus_years"
                elif years >= 3:
                    exp = "3_5_years"
                elif years >= 1:
                    exp = "1_3_years"
                else:
                    exp = "fresher"
            except ValueError:
                exp = "fresher"
        else:
            years_matches = re.findall(r'(\d+)\s*years?\s*(?:work\s+)?experience', text)
            if years_matches:
                try:
                    max_years = max(int(y) for y in years_matches)
                    if max_years >= 5:
                        exp = "5_plus_years"
                    elif max_years >= 3:
                        exp = "3_5_years"
                    else:
                        exp = "1_3_years"
                except ValueError:
                    exp = "fresher"
            else:
                exp = "fresher"
                
    # 2. Education Level Classification
    if not edu:
        pg_kws = ["post graduate", "pg degree", "postgraduate", "m.sc", "m.com", "m.a", "m.tech", "mba", "mca", "md/ms", "phd", "ph.d"]
        grad_kws = ["graduate", "degree", "b.sc", "b.com", "b.a", "b.tech", "b.e", "bba", "bca", "mbbs", "llb"]
        dip_kws = ["diploma", "iti", "polytechnic"]
        school_kws = ["10th", "12th", "hslc", "hs pass", "matric", "class x", "class xii", "intermediate", "high school"]
        
        if any(k in text for k in pg_kws):
            edu = "postgraduate"
        elif any(k in text for k in grad_kws):
            edu = "graduate"
        elif any(k in text for k in dip_kws):
            edu = "diploma_iti"
        elif any(k in text for k in school_kws):
            edu = "10th_12th"
        else:
            qual_text = str(metadata.get("qualification") or "").lower()
            if any(k in qual_text for k in pg_kws):
                edu = "postgraduate"
            elif any(k in qual_text for k in grad_kws):
                edu = "graduate"
            elif any(k in qual_text for k in dip_kws):
                edu = "diploma_iti"
            elif any(k in qual_text for k in school_kws):
                edu = "10th_12th"
            else:
                edu = "graduate"
                
    # 3. Salary Range Classification
    if not sal:
        sal_text = str(metadata.get("salary") or "").lower()
        stipend_kws = ["stipend", "apprentice", "consolidated pay", "honorarium", "internship", "per day"]
        
        sal_numbers = [int(n) for n in re.findall(r'\b\d{4,6}\b', sal_text.replace(",", ""))]
        if not sal_numbers:
            sal_numbers = [int(n) for n in re.findall(r'\b\d{4,6}\b', text.replace(",", ""))]
            
        if sal_numbers:
            max_val = max(sal_numbers)
            if max_val > 150000:
                max_val = max_val // 12
                
            if max_val >= 50000:
                sal = "above_50k"
            elif max_val >= 30000:
                sal = "30k_50k"
            elif max_val >= 15000:
                sal = "15k_30k"
            else:
                sal = "below_15k"
        elif any(k in sal_text or k in text for k in stipend_kws):
            sal = "below_15k"
        else:
            sal = "15k_30k"
            
    metadata["education_level"] = edu
    metadata["salary_range"] = sal
    metadata["experience_level"] = exp
    
    return metadata
