"""
field_extractor.py — Structured field extraction from notice text.

Extracts category-specific structured data from any combination of
title, description, and body text using regex patterns.

Usage:
    from utils.field_extractor import extract_recruitment_fields, extract_exam_fields, extract_scholarship_fields
"""

import re
from typing import Optional, Dict, Any


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _first_match(patterns: list[str], text: str, flags: int = re.IGNORECASE) -> Optional[str]:
    """Return the first captured group from the first matching pattern."""
    for pat in patterns:
        m = re.search(pat, text, flags)
        if m:
            val = m.group(1).strip()
            if val:
                return val
    return None


def _clean_amount(raw: str) -> str:
    """Normalise a raw salary/amount string."""
    raw = re.sub(r"\s+", " ", raw).strip()
    # Ensure ₹ prefix
    if not raw.startswith("₹") and not raw.lower().startswith("rs"):
        raw = "₹" + raw
    raw = re.sub(r"(?i)^rs\.?\s*", "₹", raw)
    return raw


# ---------------------------------------------------------------------------
# Salary / Pay
# ---------------------------------------------------------------------------

_SALARY_PATTERNS = [
    # "Pay Scale: ₹25000-80500" or "Salary: Rs. 35,000 per month"
    r'(?:pay\s*(?:scale|band|matrix)?|salary|stipend|remuneration|consolidated\s*pay|emolument)[^\d₹Rs]{0,20}(?:Rs\.?|₹|INR)\s*([\d,]+(?:\s*[-–to]+\s*[\d,]+)?(?:\s*(?:per\s+month|p\.?m\.?|\/month))?)',
    # "₹35,000/month" or "₹18000–22000"
    r'(?:Rs\.?|₹|INR)\s*([\d,]+(?:\s*[-–to]+\s*[\d,]+)?)\s*(?:per\s+month|p\.?m\.?|\/month|\/year|pa\.?)?',
    # "Level 6 of Pay Matrix" (7th CPC)
    r'(?:pay\s+)?(?:level|grade\s+pay)[^\d]*(\d+)(?:\s+of\s+(?:pay|7th|6th))?',
    # "PB-2 ₹9300-34800" style
    r'PB[-\s]*\d\s+(?:Rs\.?|₹)\s*([\d,]+[-–][\d,]+)',
]

def extract_salary(text: str) -> Optional[str]:
    raw = _first_match(_SALARY_PATTERNS, text)
    if raw:
        return _clean_amount(raw)
    return None


# ---------------------------------------------------------------------------
# Vacancies
# ---------------------------------------------------------------------------

_VACANCY_PATTERNS = [
    r'(\d+)\s*(?:nos?\.?|no\.?\s+of)?\s*(?:posts?|vacancies|positions?|openings?|seats?)',
    r'(?:total|no\.?\s+of|number\s+of)\s+(?:posts?|vacancies|positions?)[^\d]{0,10}(\d+)',
    r'(?:recruit|fill|appoint)\s+(\d+)\s+(?:posts?|candidates?)',
]

def extract_vacancies(text: str) -> Optional[str]:
    raw = _first_match(_VACANCY_PATTERNS, text)
    if raw:
        # Validate: must be a sensible number (1–99999)
        try:
            n = int(raw.replace(",", ""))
            if 1 <= n <= 99999:
                return f"{n:,} Posts"
        except ValueError:
            pass
    # Check for "multiple" / "various" keyword
    if re.search(r'\b(multiple|various|several)\b\s+(?:posts?|vacancies)', text, re.IGNORECASE):
        return "Multiple Posts"
    return None


# ---------------------------------------------------------------------------
# Qualification
# ---------------------------------------------------------------------------

_QUAL_PATTERNS = [
    # "Qualification: B.Tech / Graduate"
    r'(?:qualification|educational\s*qualification|minimum\s*qualification)[^\n:]{0,5}:\s*([^\n.;]{10,120})',
    # "Degree in ...", "Diploma in ..."
    r'(?:degree|diploma|certificate)\s+in\s+([A-Za-z0-9\s/,&()]{5,80})',
    # "10+2 / Class 12 / Graduate / Post Graduate"
    r'\b(10\+2|10\+2\/Intermediate|Class\s+(?:10|12|VIII|X|XII)|Matriculation|Higher\s+Secondary|Intermediate|Graduate|Post\s+Graduate|B\.?Sc\.?|B\.?Tech\.?|B\.?E\.?|M\.?Sc\.?|M\.?Tech\.?|MBA|MCA|MBBS|BDS|LLB|PhD)\b',
    # "Passed class X/XII from ..."
    r'(?:passed|pass)\s+(class\s+(?:10|12|X|XII|VIII)|matriculation|higher\s+secondary)',
]

def extract_qualification(text: str) -> Optional[str]:
    return _first_match(_QUAL_PATTERNS, text)


# ---------------------------------------------------------------------------
# Dates (last/closing date for applications)
# ---------------------------------------------------------------------------

# Months spelled out or abbreviated
_MONTH = r'(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'

_LAST_DATE_PATTERNS = [
    r'(?:last\s+date|closing\s+date|apply\s+(?:by|before|on\s+or\s+before)|application\s+(?:closes?|deadline)|submit\s+(?:by|before))[^\d]*(\d{1,2}\s*[-/\.]\s*\d{1,2}\s*[-/\.]\s*\d{2,4})',
    rf'(?:last\s+date|closing\s+date|apply\s+(?:by|before)|deadline)[^\d]*(\d{{1,2}}\s+{_MONTH}\s+\d{{2,4}})',
    rf'(?:last\s+date|closing\s+date|deadline)\s*[:\-]?\s*({_MONTH}\s+\d{{1,2}},?\s+\d{{4}})',
    r'(?:last\s+date|closing\s+date)[^\d]*(\d{4}-\d{2}-\d{2})',
]

def extract_last_date(text: str) -> Optional[str]:
    return _first_match(_LAST_DATE_PATTERNS, text)


# ---------------------------------------------------------------------------
# Advertisement / Reference number
# ---------------------------------------------------------------------------

_ADVT_PATTERNS = [
    r'(?:advt\.?|advertisement)\s*(?:no\.?|number)?\s*[:\-]?\s*([A-Z0-9\-/\.]+)',
    r'(?:ref\.?|reference)\s*(?:no\.?|number)\s*[:\-]?\s*([A-Z0-9\-/\.]+)',
    r'(?:notification|circular)\s*(?:no\.?|number)\s*[:\-]?\s*([A-Z0-9\-/\.]+)',
]

def extract_advt_no(text: str) -> Optional[str]:
    return _first_match(_ADVT_PATTERNS, text, flags=re.IGNORECASE)


# ---------------------------------------------------------------------------
# Exam-specific fields
# ---------------------------------------------------------------------------

_EXAM_DATE_PATTERNS = [
    rf'(?:exam(?:ination)?\s+(?:date|scheduled?)|written\s+test|test\s+date)[^\d]*(\d{{1,2}}\s+{_MONTH}\s+\d{{2,4}})',
    r'(?:exam(?:ination)?\s+(?:date|scheduled?)|written\s+test)[^\d]*(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})',
    rf'(?:exam(?:ination)?|written\s+test|viva.?voce)\s+(?:is\s+)?(?:on|scheduled\s+for|will\s+be\s+held\s+on)\s+(\d{{1,2}}\s+{_MONTH}\s+\d{{2,4}})',
]

def extract_exam_date(text: str) -> Optional[str]:
    return _first_match(_EXAM_DATE_PATTERNS, text)


_ADMIT_CARD_PATTERNS = [
    rf'(?:admit\s+card|hall\s+ticket)\s+(?:available|download|from|date)[^\d]*(\d{{1,2}}\s+{_MONTH}\s+\d{{2,4}})',
    r'(?:admit\s+card|hall\s+ticket)\s+(?:available|download|from|date)[^\d]*(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})',
]

def extract_admit_card_date(text: str) -> Optional[str]:
    return _first_match(_ADMIT_CARD_PATTERNS, text)


_EXAM_MODE_PATTERNS = [
    r'\b(online|offline|OMR[-\s]based|computer[-\s]based|CBT|pen[\s&]+paper|written)\b\s*(?:exam(?:ination)?|test|mode)?',
]

def extract_exam_mode(text: str) -> Optional[str]:
    raw = _first_match(_EXAM_MODE_PATTERNS, text)
    if raw:
        return raw.strip().title()
    return None


# ---------------------------------------------------------------------------
# Scholarship-specific fields
# ---------------------------------------------------------------------------

_AWARD_PATTERNS = [
    r'(?:award|scholarship|stipend|amount|grant)[^\d₹Rs]{0,20}(?:Rs\.?|₹|INR)\s*([\d,]+(?:\s*(?:per\s+(?:year|month|annum)|p\.?a\.?|pm|\/year|\/month))?)',
    r'(?:Rs\.?|₹|INR)\s*([\d,]+)\s*(?:per\s+(?:year|month|annum)|p\.?a\.?)',
    r'(\d+(?:,\d+)*)\s*(?:per\s+(?:year|annum)|p\.?a\.?)\s*(?:scholarship|award|grant)',
]

def extract_award_amount(text: str) -> Optional[str]:
    raw = _first_match(_AWARD_PATTERNS, text)
    if raw:
        return _clean_amount(raw)
    return None


_SCHOLARSHIP_LEVEL_PATTERNS = [
    r'\b(pre[-\s]matric|post[-\s]matric|pre[-\s]metric|post[-\s]metric)\b',
    r'\b(class\s+(?:IX|X|XI|XII|9|10|11|12))\b',
    r'\b(under[-\s]?graduate|post[-\s]?graduate|UG|PG|doctoral|PhD)\b',
    r'\b(merit[-\s]cum[-\s]means|means[-\s]cum[-\s]merit|MCM)\b',
]

def extract_scholarship_level(text: str) -> Optional[str]:
    raw = _first_match(_SCHOLARSHIP_LEVEL_PATTERNS, text)
    if raw:
        return raw.strip().title()
    return None


_APPLICATION_MODE_PATTERNS = [
    r'(?:apply|application)\s+(?:online|through|via|at)\s+([^\s,.\n]+(?:\.[a-z]{2,4})?)',
    r'(?:online|offline|walk[-\s]in)\s+(?:application|interview|mode)',
    r'(apply\s+(?:online|offline|via\s+post|through\s+email))',
]

def extract_application_mode(text: str) -> Optional[str]:
    return _first_match(_APPLICATION_MODE_PATTERNS, text)


# ---------------------------------------------------------------------------
# Age / Eligibility
# ---------------------------------------------------------------------------

_AGE_PATTERNS = [
    r'(?:age\s+(?:limit|criteria|relaxation)?)[^\d]*(\d+)\s*[-–to]+\s*(\d+)\s*years?',
    r'(?:minimum\s+age|max(?:imum)?\s+age)[^\d]*(\d+)\s*years?',
    r'(\d+)\s*[-–]\s*(\d+)\s*years?\s*(?:of\s+age|age)',
]

def extract_age_limit(text: str) -> Optional[str]:
    for pat in _AGE_PATTERNS:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            groups = [g for g in m.groups() if g]
            if len(groups) >= 2:
                return f"{groups[0]}–{groups[1]} years"
            elif len(groups) == 1:
                return f"Up to {groups[0]} years"
    return None


# ---------------------------------------------------------------------------
# Main extraction functions per category
# ---------------------------------------------------------------------------

def extract_recruitment_fields(title: str, description: str = "", body_text: str = "") -> Dict[str, Any]:
    """
    Extract structured recruitment/job fields from available text.
    Returns a dict with keys: salary, vacancies, qualification, last_date, advt_no, age_limit.
    Values are strings or None.
    """
    combined = " ".join(filter(None, [title, description, body_text]))
    return {
        "salary": extract_salary(combined),
        "vacancies": extract_vacancies(combined),
        "qualification": extract_qualification(combined),
        "last_date": extract_last_date(combined),
        "advt_no": extract_advt_no(combined),
        "age_limit": extract_age_limit(combined),
    }


def extract_exam_fields(title: str, description: str = "", body_text: str = "") -> Dict[str, Any]:
    """
    Extract structured exam fields.
    Returns: exam_date, admit_card_date, last_date, eligibility, exam_mode.
    """
    combined = " ".join(filter(None, [title, description, body_text]))
    return {
        "exam_date": extract_exam_date(combined),
        "admit_card_date": extract_admit_card_date(combined),
        "last_date": extract_last_date(combined),
        "qualification": extract_qualification(combined),
        "age_limit": extract_age_limit(combined),
        "exam_mode": extract_exam_mode(combined),
    }


def extract_scholarship_fields(title: str, description: str = "", body_text: str = "") -> Dict[str, Any]:
    """
    Extract structured scholarship fields.
    Returns: award_amount, last_date, level, qualification, application_mode.
    """
    combined = " ".join(filter(None, [title, description, body_text]))
    return {
        "award_amount": extract_award_amount(combined),
        "last_date": extract_last_date(combined),
        "level": extract_scholarship_level(combined),
        "qualification": extract_qualification(combined),
        "age_limit": extract_age_limit(combined),
        "application_mode": extract_application_mode(combined),
    }


def extract_fields_for_category(category: str, title: str, description: str = "", body_text: str = "") -> Dict[str, Any]:
    """
    Dispatch to the correct extractor based on notice category.
    category should be one of: 'recruitment', 'exam', 'scholarship', 'result', 'admission', 'notice'
    """
    cat = category.lower().strip()
    if cat in ("recruitment", "job"):
        return extract_recruitment_fields(title, description, body_text)
    elif cat in ("exam", "result"):
        return extract_exam_fields(title, description, body_text)
    elif cat in ("scholarship",):
        return extract_scholarship_fields(title, description, body_text)
    else:
        # For admission/notice: try recruitment fields as best effort
        return extract_recruitment_fields(title, description, body_text)
