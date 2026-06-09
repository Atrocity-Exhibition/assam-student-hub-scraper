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
from google import genai
from google.genai import types
import tempfile

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
client = genai.Client(api_key=gemini_key)

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
        
    # If description is too short
    if len(desc_clean) < 120:
        return True
        
    return False

def is_generic_title(title: str) -> bool:
    """
    Check if the notice title is a generic word (e.g. "Notice", "Recruitment", "Tender").
    """
    t_clean = title.strip().lower()
    t_clean = re.sub(r'[^\w\s]', '', t_clean)
    generic_words = {
        "notice", "notification", "recruitment", "tender", "quotation", "advertisement",
        "advt", "circular", "news", "announcement", "result", "results", "admission",
        "admissions", "exam", "exams", "examination", "examinations", "routines", "routine"
    }
    words = t_clean.split()
    if len(words) <= 2:
        if all(w in generic_words for w in words):
            return True
    return False

def extract_pdf_text(attachment_url: str) -> tuple[str, str | None]:
    """
    Download PDF, save to a temporary file, and extract text from the first 4 pages.
    Returns a tuple of (extracted_text, temp_file_path).
    """
    logger.info(f"Downloading PDF from: {attachment_url}")
    temp_file_path = None
    try:
        # Disable SSL verification warnings as government servers often have self-signed certificates
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        response = requests.get(attachment_url, timeout=(8, 12), verify=False)
        if response.status_code != 200:
            logger.warning(f"Failed to download PDF. HTTP Status: {response.status_code}")
            return "", None
            
        # Write to a temporary file so Gemini Files API can ingest it if it is scanned
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(response.content)
            temp_file_path = tmp.name
            
        reader = pypdf.PdfReader(temp_file_path)
        
        text_parts = []
        max_pages = min(4, len(reader.pages))
        logger.info(f"Extracting text from first {max_pages} page(s)...")
        
        for i in range(max_pages):
            page_text = reader.pages[i].extract_text()
            if page_text:
                text_parts.append(page_text)
                
        full_text = "\n".join(text_parts).strip()
        return full_text, temp_file_path
    except Exception as e:
        logger.error(f"Error downloading or parsing PDF: {e}")
        return "", temp_file_path

def enrich_notice(notice: dict, pdf_text: str, pdf_file_path: str | None) -> bool:
    """
    Send text (or upload scanned PDF) to Google Gemini to get structured description and metadata,
    and update Supabase.
    """
    notice_id = notice["id"]
    title = notice["title"]
    category = notice.get("category", "notice")
    
    logger.info(f"Enriching notice ID {notice_id}: '{title[:60]}...'")
    
    # Check if we have extracted text to parse.
    # If PDF has no readable text (scanned image), upload the file to Gemini if available.
    is_scanned = len(pdf_text) < 150
    uploaded_file = None
    
    try:
        if is_scanned and pdf_file_path and os.path.exists(pdf_file_path):
            logger.info(f"PDF has negligible readable text ({len(pdf_text)} chars). Using multimodal upload.")
            try:
                uploaded_file = client.files.upload(file=pdf_file_path)
                logger.info(f"Uploaded file to Gemini Files API: {uploaded_file.name}")
                
                # Wait for processing if necessary
                import time
                state = uploaded_file.state
                while state.name == "PROCESSING":
                    logger.info("Waiting for file to be processed...")
                    time.sleep(2)
                    uploaded_file = client.files.get(name=uploaded_file.name)
                    state = uploaded_file.state
                    
                if state.name != "ACTIVE":
                    raise Exception(f"File state is not ACTIVE: {state.name}")
                    
            except Exception as upload_err:
                logger.warning(f"Failed to upload file to Gemini: {upload_err}. Falling back to title-only extraction.")
                uploaded_file = None

        if is_scanned and not uploaded_file:
            logger.warning("Falling back to title-only description extraction (no multimodal upload available).")
            prompt = f"""You are an expert assistant for a student and recruitment notices portal.
            The attachment for the notice titled "{title}" (Category: {category}) is a scanned PDF image, so its text cannot be read directly.
            
            Based ONLY on the title:
            1. Determine if the notice is relevant to students, scholars, or job seekers (e.g. recruitments, admissions, exams, scholarships, academic fees, application guidelines, routines, results). Set "is_relevant" to true. If it is irrelevant (e.g. tenders, procurement/quotation notices, administrative transfer or retirement orders, internal staff meetings, audit reports, employee holiday announcements), set "is_relevant" to false.
            2. Provide a short reason in "relevance_reason".
            3. The notice title is "{title}". If it is a very generic word (e.g., just 'Notice' or 'Recruitment'), suggest a descriptive and clean title under 100 characters in the "refined_title" key. Otherwise, set "refined_title" to null.
            4. Generate a professional, clean, and informative summary/description of 1 to 2 sentences suitable for a notification card.
            5. Set all other metadata fields to null.
            
            Response format: You MUST respond with a valid JSON object matching this schema exactly:
            {{
              "description": "...",
              "refined_title": "..." or null,
              "is_relevant": true/false,
              "relevance_reason": "...",
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
            contents = [prompt]
        elif uploaded_file:
            # Multimodal prompt with the uploaded file object
            prompt = f"""You are an expert educational and recruitment notifications helper.
            Analyze the attached official notification document titled "{title}" (Category: {category}).
            
            Since this document is a scanned image/PDF, visually read the document text and extract the following information:
            1. Determine if the notice is relevant to students, scholars, or job seekers (e.g. recruitments, admissions, exams, scholarships, academic fees, application guidelines, routines, results). Set "is_relevant" to true. If it is irrelevant (e.g. tenders, procurement/quotation notices, administrative transfer or retirement orders, internal staff meetings, audit reports, employee holiday announcements), set "is_relevant" to false.
            2. Provide a short reason in "relevance_reason".
            3. The notice title is "{title}". If it is a very generic word (e.g., just 'Notice' or 'Recruitment'), suggest a descriptive and clean title under 100 characters in the "refined_title" key based on the document contents. Otherwise, set "refined_title" to null.
            4. A professional, clean, and informative summary/description of 2 to 3 sentences suitable for a notification card on a student portal. Summarize what the notice is, who it is for, and key actions required.
            5. Important metadata fields matching these keys exactly:
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
              "refined_title": "..." or null,
              "is_relevant": true/false,
              "relevance_reason": "...",
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
            """
            contents = [uploaded_file, prompt]
        else:
            prompt = f"""You are an expert educational and recruitment notifications helper.
            Analyze the following text extracted from an official notification document titled "{title}" (Category: {category}).
            
            Extract the following information:
            1. Determine if the notice is relevant to students, scholars, or job seekers (e.g. recruitments, admissions, exams, scholarships, academic fees, application guidelines, routines, results). Set "is_relevant" to true. If it is irrelevant (e.g. tenders, procurement/quotation notices, administrative transfer or retirement orders, internal staff meetings, audit reports, employee holiday announcements), set "is_relevant" to false.
            2. Provide a short reason in "relevance_reason".
            3. The notice title is "{title}". If it is a very generic word (e.g., just 'Notice' or 'Recruitment'), suggest a descriptive and clean title under 100 characters in the "refined_title" key based on the document contents. Otherwise, set "refined_title" to null.
            4. A professional, clean, and informative summary/description of 2 to 3 sentences suitable for a notification card on a student portal. Summarize what the notice is, who it is for, and key actions required.
            5. Important metadata fields matching these keys exactly:
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
              "refined_title": "..." or null,
              "is_relevant": true/false,
              "relevance_reason": "...",
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
            contents = [prompt]
            
        # Call Gemini with a retry loop and fallback models to handle temporary 503 or 429 errors
        import time
        models_to_try = [
            "gemini-2.5-flash",
            "gemini-3.1-flash-lite",
            "gemini-flash-lite-latest",
            "gemini-2.5-flash-lite",
            "gemini-flash-latest"
        ]
        response = None
        last_exception = None
        
        for model_name in models_to_try:
            logger.info(f"Attempting content generation using model: {model_name}")
            max_retries = 3
            backoff = 3
            success = False
            for attempt in range(max_retries):
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=contents,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json"
                        )
                    )
                    success = True
                    break
                except Exception as gen_err:
                    last_exception = gen_err
                    err_msg = str(gen_err).lower()
                    is_retryable = any(x in err_msg for x in ["503", "429", "temporary", "demand", "unavailable", "exhausted"])
                    if is_retryable and attempt < max_retries - 1:
                        sleep_time = backoff ** (attempt + 1)
                        logger.warning(f"Gemini API error for model {model_name} (Attempt {attempt+1}/{max_retries}): {gen_err}. Retrying in {sleep_time}s...")
                        time.sleep(sleep_time)
                    else:
                        logger.warning(f"Model {model_name} failed with error: {gen_err}")
                        break
            if success:
                break
        else:
            if last_exception:
                raise last_exception
            else:
                raise Exception("All configured models failed to generate content.")
        
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
            if uploaded_file:
                current_metadata["ai_multimodal_extracted"] = True
            else:
                current_metadata["ai_scanned_fallback"] = True
            
        # Write back to Supabase
        update_data = {
            "description": description_ai,
            "metadata": current_metadata,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Check relevance
        is_relevant = ai_data.get("is_relevant", True)
        if is_relevant is False:
            update_data["is_active"] = False
            logger.info(f"Notice ID {notice_id} classified as IRRELEVANT (Reason: {ai_data.get('relevance_reason')}). Setting is_active = False.")
            
        # Check title refinement
        refined_title = ai_data.get("refined_title")
        if refined_title and len(refined_title.strip()) > 5:
            update_data["title"] = refined_title.strip()
            logger.info(f"Notice ID {notice_id} title refined from '{title}' to '{refined_title.strip()}'")
            
        supabase.table("notices").update(update_data).eq("id", notice_id).execute()
        logger.info(f"Successfully enriched Notice ID {notice_id}!")
        return True
        
    except Exception as e:
        logger.error(f"Failed to query Gemini or update Supabase: {e}")
        return False
        
    finally:
        # Clean up the file from Gemini Files API if we uploaded one
        if uploaded_file:
            try:
                client.files.delete(name=uploaded_file.name)
                logger.info(f"Deleted PDF file from Gemini Files API: {uploaded_file.name}")
            except Exception as cleanup_err:
                logger.warning(f"Failed to delete file from Gemini Files API: {cleanup_err}")

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
            url = notice.get("attachment_url")
            pdf_text = ""
            temp_file_path = None
            if url and url.lower().startswith("http") and url.lower().endswith(".pdf"):
                pdf_text, temp_file_path = extract_pdf_text(url)
                
            try:
                success = enrich_notice(notice, pdf_text, temp_file_path)
                if success:
                    enriched_count += 1
            finally:
                if temp_file_path and os.path.exists(temp_file_path):
                    try:
                        os.remove(temp_file_path)
                        logger.info(f"Cleaned up local temporary file: {temp_file_path}")
                    except Exception as e:
                        logger.warning(f"Failed to remove local temporary file: {e}")
                
        logger.info(f"Completed run. Successfully enriched {enriched_count} / {len(batch)} notices.")
        
    except Exception as e:
        logger.error(f"Database error during main execution: {e}")

if __name__ == "__main__":
    main()
