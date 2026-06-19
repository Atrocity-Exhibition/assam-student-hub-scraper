import os
import re
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_dotenv(dotenv_path)

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

if not supabase_url or not supabase_key:
    print("Error: SUPABASE_URL or SUPABASE_KEY not found in environment.")
    exit(1)

supabase = create_client(supabase_url, supabase_key)

EXCLUDED_ACADEMIC_SLUGS = [
    "gauhati-university",
    "cotton-university",
    "dibrugarh-university",
    "tezpur-university",
    "bodoland-university",
    "mangaldai-college",
    "assam-university",
    "astu",
    "krishna-kanta-handiqui-state-open-university",
    "assam-womens-university",
]

def is_academic_institution(slug, name):
    if not slug:
        slug = ""
    if not name:
        name = ""
    slug_lower = slug.lower()
    name_lower = name.lower()
    
    return (
        slug_lower in EXCLUDED_ACADEMIC_SLUGS or
        "college" in slug_lower or
        "university" in slug_lower or
        "uni-" in slug_lower or
        slug_lower.startswith("uni") or
        "iit" in slug_lower or
        "lnipe" in slug_lower or
        "college" in name_lower or
        "university" in name_lower or
        "institute" in name_lower or
        "school" in name_lower
    )

def is_old_notice(title, description):
    text = f"{title or ''} {description or ''}"
    
    # Match academic years like 2015, 2016, ..., 2025, or ranges like 2017-18, 2017-2018, 2024-25, etc.
    # We want to identify any year 2010 to 2025.
    years_found = []
    
    # 1. Match 4-digit years: 2010 to 2025
    four_digit_matches = re.findall(r"\b(201\d|202[0-5])\b", text)
    years_found.extend(four_digit_matches)
    
    # 2. Match ranges like 17-18, 18-19, 23-24, 24-25
    # Let's check for pairs of 2-digit years between 10 and 25
    two_digit_range_matches = re.findall(r"\b(1\d|2[0-5])-(1\d|2[0-5])\b", text)
    if two_digit_range_matches:
        for m1, m2 in two_digit_range_matches:
            years_found.append(f"20{m1}")
            years_found.append(f"20{m2}")
            
    # Check if we contain current/future years (2026, 2027)
    contains_current_or_future = bool(re.search(r"\b(202[6-9]|203\d)\b", text))
    
    # If we found old years and do NOT contain current or future years, it's old!
    return len(years_found) > 0 and not contains_current_or_future

def main():
    print("Fetching all notices from database...")
    # Fetch all notices (doing paginated fetch to handle potential large volume)
    all_notices = []
    limit = 1000
    offset = 0
    
    while True:
        response = supabase.table("notices").select("id, title, description, institution, institution_slug").range(offset, offset + limit - 1).execute()
        data = response.data
        if not data:
            break
        all_notices.extend(data)
        if len(data) < limit:
            break
        offset += limit

    print(f"Total notices found in database: {len(all_notices)}")
    
    old_notice_ids = []
    print("\nScanning for old academic notices...")
    print(f"{'ID':<8} | {'Institution':<25} | {'Title'}")
    print("-" * 80)
    
    for notice in all_notices:
        inst_slug = notice.get("institution_slug")
        inst_name = notice.get("institution")
        
        # Check if it belongs to college/university
        if is_academic_institution(inst_slug, inst_name):
            title = notice.get("title", "")
            desc = notice.get("description", "")
            
            if is_old_notice(title, desc):
                print(f"{notice['id']:<8} | {inst_name[:25]:<25} | {title[:40]}")
                old_notice_ids.append(notice["id"])
                
    print(f"\nTotal old notices identified: {len(old_notice_ids)}")
    
    if not old_notice_ids:
        print("No old notices to delete.")
        return
        
    print("\nPermanently deleting identified old notices from database...")
    
    # Delete in batches of 100 to avoid request limits
    batch_size = 100
    deleted_count = 0
    for i in range(0, len(old_notice_ids), batch_size):
        batch = old_notice_ids[i:i+batch_size]
        response = supabase.table("notices").delete().in_("id", batch).execute()
        deleted_count += len(response.data or [])
        print(f"Deleted batch {i//batch_size + 1}: {len(response.data or [])} records.")
        
    print(f"\nCleanup complete. Successfully deleted {deleted_count} old notices.")

if __name__ == "__main__":
    main()
