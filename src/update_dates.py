import os
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_dotenv(dotenv_path)

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

supabase = create_client(supabase_url, supabase_key)

def main():
    print("Querying manually inserted notices...")
    response = supabase.table("notices").select("id, title, posted_at, slug").eq("institution_slug", "mangaldai-college").execute()
    notices = response.data or []
    
    # We want to match titles and update their dates to today (2026-06-19)
    target_dates = {
        "Notice for Spot Admission (Academic Session 2026-27)": "2026-06-19T12:00:00+00:00",
        "FYUGP 2nd Semester Arrear Examination Form Fill-up Notice": "2026-06-19T11:50:00+00:00",
        "FYUGP 4th Semester Arrear Examination Form Fill-up Notice": "2026-06-19T11:40:00+00:00",
        "Publication of 2nd Merit List for Undergraduate Admission (AY 2026-27)": "2026-06-19T11:30:00+00:00",
        "Availability of FYUGP 4th Semester Marksheets": "2026-06-19T11:20:00+00:00",
        "Publication of 1st Merit List for Undergraduate Admission (AY 2026-27)": "2026-06-19T11:10:00+00:00",
        "Rescheduling of FYUGP 2nd Semester Examinations 2026": "2026-06-19T11:00:00+00:00"
    }
    
    updated_count = 0
    for notice in notices:
        title = notice["title"]
        if title in target_dates:
            new_date = target_dates[title]
            print(f"Updating: '{title}'")
            print(f"    Old Date: {notice['posted_at']} -> New Date: {new_date}")
            
            up_response = supabase.table("notices").update({"posted_at": new_date}).eq("id", notice["id"]).execute()
            if up_response.data:
                updated_count += 1
                
    print(f"\nDone. Successfully updated {updated_count} notices to today.")

if __name__ == "__main__":
    main()
