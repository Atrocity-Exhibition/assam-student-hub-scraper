import os
import io
import sys
import re
import json
import logging
import requests
import argparse
from datetime import datetime, timezone
from dotenv import load_dotenv
from supabase import create_client
import pypdf
import google.generativeai as genai

# Setup Logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("AIEnricher")

# Resolve path to .env in scrapers/ directory
dotenv_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path)

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
gemini_key = os.getenv("GEMINI_API_KEY")

if not supabase_url or not supabase_key:
    logger.error("SUPABASE_URL or SUPABASE_KEY not found in environment. Exiting.")
    sys.exit(1)

if not gemini_key:
    logger.warning("GEMINI_API_KEY not found in environment. AI enrichment will be skipped.")
    sys.exit(0)

# Configure clients
supabase = create_client(supabase_url, supabase_key)
genai.configure(api_key=gemini_key)

def is_placeholder_description(desc: str, title: str) -> bool:
    """
    Check if the existing description is a placeholder or generic text.
    """
    if not desc:
        return True
    
    desc_clean = desc.strip()
    if not desc_clean:
        return True
        
    # Check common placeholder patterns
    if desc_clean.startswith("Official update from"):
        return True
    if "Please refer to the notice details page or attachment" in desc_clean:
        return True
    if desc_clean == f"Sourced from {title} announcement board.":
        return True
        
    # If description is too short (repeats the title)
    if len(desc_clean) < 120 and title.lower() in desc_clean.lower():
        return True
        
    return False

def extract_pdf_text(attachment_url: str) -> str:
    """
    Download PDF and extract text from the first 4 pages.
    """
    logger.info(f"Downloading PDF from: {attachment_url}")
    try:
        response = requests.get(attachment_url, timeout=(8, 12))
        if response.status_code != 200:
            logger.warning(f"Failed to download PDF. HTTP Status: {response.status_code}")
            return ""
            
        pdf_file = io.BytesIO(response.content)
        reader = pypdf.PdfReader(pdf_file)
        
        text_parts = []
        max_pages = min(4, len(reader.pages))
        logger.info(f"Extracting text from first {max_pages} page(s)...")
        
        for i in range(max_pages):
            page_text = reader.pages[i].extract_text()
            if page_text:
                text_parts.append(page_text)
                
        full_text = "\n".join(text_parts).strip()
        return full_text
    except Exception as e:
        logger.error(f"Error downloading or parsing PDF: {e}")
        return ""

def enrich_notice(notice: dict, pdf_text: str) -> bool:
    """
    Send text to Google Gemini to get structured description and metadata,
    and update Supabase.
    """
    notice_id = notice["id"]
    title = notice["title"]
    category = notice.get("category", "notice")
    
    logger.info(f"Enriching notice ID {notice_id}: '{title[:60]}...'")
    
    # Check if we have extracted text to parse.
    # If PDF has no readable text (scanned image), use a title-based fallback prompt.
    is_scanned = len(pdf_text) < 150
    
    if is_scanned:
        logger.warning(f"PDF has negligible readable text ({len(pdf_text)} chars). Falling back to title-only extraction.")
        prompt = f"""You are an expert assistant for a student and recruitment notices portal.
        The attachment for the notice titled "{title}" (Category: {category}) is a scanned PDF image, so its text cannot be read directly.
        
        Based ONLY on the title, generate:
        1. A professional, clean, and informative summary/description of 1 to 2 sentences suitable for a notification card.
        2. Set all other metadata fields to null.
        
        Response format: You MUST respond with a valid JSON object matching this schema exactly:
        {{
          "description": "...",
          "vacancies": null,
          "qualification": null,
          "last_date": null,
          "salary": null,
          "advt_no": null,
          "age_limit": null,
          "exam_date": null,
          "admit_card_date": null,
          "exam_mode": null,
          "award_amount": null,
          "level": null,
          "application_mode": null
        }}
        """
    else:
        prompt = f"""You are an expert educational and recruitment notifications helper.
        Analyze the following text extracted from an official notification document titled "{title}" (Category: {category}).
        
        Extract the following information:
        1. A professional, clean, and informative summary/description of 2 to 3 sentences suitable for a notification card on a student portal. Summarize what the notice is, who it is for, and key actions required. Do not include introductory text like "Here is a summary".
        2. Important metadata fields matching these keys exactly:
           - "vacancies": Total number of vacancies/posts/seats mentioned (integer or null).
           - "qualification": Educational qualification requirements (short string under 100 chars, e.g. "Graduate in any discipline", "Class 12 passed", or null).
           - "last_date": The final deadline/last date to apply in YYYY-MM-DD format (string or null).
           - "salary": Salary/pay scale/stipend information (short string, e.g. "Rs. 14,000 - 60,500 + GP Rs. 8,700" or null).
           - "advt_no": Advertisement reference number (string or null).
           - "age_limit": Age eligibility criteria (short string, e.g. "18 - 40 years as of 01-01-2026" or null).
           
        If the category is "exam", also try to extract:
           - "exam_date": The date of the examination (short string or null).
           - "admit_card_date": The date of admit card release (short string or null).
           - "exam_mode": Mode of exam (e.g. "OMR-based", "Written Test", "Computer Practical Test", or null).
           
        If the category is "scholarship", also try to extract:
           - "award_amount": Financial award amount (short string, e.g. "Rs. 10,000 per annum" or null).
           - "level": Level of study (e.g. "PG", "UG", "Class 11/12", or null).
           - "application_mode": Mode of application (e.g. "Online via National Scholarship Portal", "Offline", or null).
           
        Response format: You MUST respond with a valid JSON object matching this schema exactly:
        {{
          "description": "...",
          "vacancies": ...,
          "qualification": ...,
          "last_date": ...,
          "salary": ...,
          "advt_no": ...,
          "age_limit": ...,
          "exam_date": ...,
          "admit_card_date": ...,
          "exam_mode": ...,
          "award_amount": ...,
          "level": ...,
          "application_mode": ...
        }}
        
        Make sure all JSON keys are present. Set any fields that cannot be found to null.
        
        Document Text:
        {pdf_text[:10000]}
        """
        
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        
        ai_data = json.loads(response.text)
        description_ai = ai_data.get("description")
        
        if not description_ai or len(description_ai.strip()) < 10:
            logger.warning("Gemini returned an empty or invalid description. Skipping update.")
            return False
            
        # Parse current metadata
        current_metadata = notice.get("metadata") or {}
        
        # Merge key fields
        for k, v in ai_data.items():
            if k != "description" and v is not None:
                current_metadata[k] = v
                
        # Mark as enriched
        current_metadata["ai_enriched"] = True
        if is_scanned:
            current_metadata["ai_scanned_fallback"] = True
            
        # Write back to Supabase
        update_data = {
            "description": description_ai,
            "metadata": current_metadata,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Parse last_date to update posted_at/deadline if suitable, or let it live in metadata
        # (The frontend reads last_date directly from metadata)
        
        supabase.table("notices").update(update_data).eq("id", notice_id).execute()
        logger.info(f"Successfully enriched Notice ID {notice_id}!")
        return True
        
    except Exception as e:
        logger.error(f"Failed to query Gemini or update Supabase: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="AssamStudentHub AI Notice Enricher using Google Gemini API")
    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=10,
        help="Maximum number of notices to process in this run (default: 10)"
    )
    args = parser.parse_args()
    
    logger.info("Starting AI Enrichment pipeline")
    
    # Query active notices with attachments
    try:
        response = supabase.table("notices")\
            .select("id, title, description, category, attachment_url, metadata")\
            .eq("is_active", True)\
            .execute()
            
        all_notices = response.data or []
        logger.info(f"Retrieved {len(all_notices)} active notices from database.")
        
        # Filter notices needing enrichment in Python
        to_enrich = []
        for notice in all_notices:
            url = notice.get("attachment_url")
            # Must have a valid HTTP PDF attachment
            if not url or not url.lower().startswith("http") or not url.lower().endswith(".pdf"):
                continue
                
            metadata = notice.get("metadata") or {}
            # Skip if already enriched
            if metadata.get("ai_enriched") is True:
                continue
                
            # Check description is placeholder
            desc = notice.get("description")
            title = notice.get("title", "")
            if is_placeholder_description(desc, title):
                to_enrich.append(notice)
                
        logger.info(f"Found {len(to_enrich)} notices eligible for AI enrichment.")
        
        if not to_enrich:
            logger.info("No notices require enrichment. Done!")
            return
            
        # Limit to the requested batch size
        batch = to_enrich[:args.limit]
        logger.info(f"Processing batch of {len(batch)} notices in this run.")
        
        enriched_count = 0
        for notice in batch:
            pdf_text = extract_pdf_text(notice["attachment_url"])
            success = enrich_notice(notice, pdf_text)
            if success:
                enriched_count += 1
                
        logger.info(f"Completed run. Successfully enriched {enriched_count} / {len(batch)} notices.")
        
    except Exception as e:
        logger.error(f"Database error during main execution: {e}")

if __name__ == "__main__":
    main()
