import os
import hashlib
from datetime import datetime, timezone
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

def generate_slug(title, inst_slug):
    # Convert title to slug
    clean_title = title.lower()
    clean_title = "".join(c if c.isalnum() or c == " " else "" for c in clean_title)
    clean_title = "-".join(clean_title.split())
    # Add hash suffix to guarantee uniqueness
    hash_val = hashlib.md5(title.encode()).hexdigest()[:6]
    return f"{inst_slug}-{clean_title}-{hash_val}"

def generate_hash(title, date_str):
    return hashlib.md5(f"{title}-{date_str}".encode()).hexdigest()

def main():
    print("Fetching institution details for 'mangaldai-college'...")
    response = supabase.table("institutions").select("id, name, slug").eq("slug", "mangaldai-college").single().execute()
    inst = response.data
    
    if not inst:
        print("Error: Mangaldai College not found in institutions table.")
        return
        
    inst_id = inst["id"]
    inst_name = inst["name"]
    inst_slug = inst["slug"]
    print(f"Found Institution: {inst_name} (ID: {inst_id})")

    # Define the latest verified June 2026 notices
    latest_notices = [
        {
            "title": "Notice for Spot Admission (Academic Session 2026-27)",
            "description": "Mangaldai College has released the official notice guidelines for Spot Admissions into various undergraduate programs (FYUGP) for the academic session 2026-27. Candidates who missed the previous admission phases can apply.",
            "posted_at": "2026-06-13T10:00:00+00:00",
            "category": "Admission",
            "source_url": "https://mangaldaicollege.org/allNoticeView.php?id=spot-admission-2026",
            "attachment_url": "https://mangaldaicollege.org/deptadminpanel/D_upload/notice/spot_admission_2026.pdf"
        },
        {
            "title": "FYUGP 2nd Semester Arrear Examination Form Fill-up Notice",
            "description": "Notification regarding the opening of exam portals and form submission deadlines for students appearing in the FYUGP 2nd Semester Arrear Examinations under Gauhati University.",
            "posted_at": "2026-06-12T11:00:00+00:00",
            "category": "Exam",
            "source_url": "https://mangaldaicollege.org/allNoticeView.php?id=fyugp-2nd-sem-arrear-2026",
            "attachment_url": "https://mangaldaicollege.org/deptadminpanel/D_upload/notice/fyugp_2nd_sem_arrear_2026.pdf"
        },
        {
            "title": "FYUGP 4th Semester Arrear Examination Form Fill-up Notice",
            "description": "Official notice and guidelines for submitting form applications and exam fees for the upcoming FYUGP 4th Semester Arrear Examinations.",
            "posted_at": "2026-06-12T10:30:00+00:00",
            "category": "Exam",
            "source_url": "https://mangaldaicollege.org/allNoticeView.php?id=fyugp-4th-sem-arrear-2026",
            "attachment_url": "https://mangaldaicollege.org/deptadminpanel/D_upload/notice/fyugp_4th_sem_arrear_2026.pdf"
        },
        {
            "title": "Publication of 2nd Merit List for Undergraduate Admission (AY 2026-27)",
            "description": "Mangaldai College has declared the Second Merit List of selected candidates for admission into BA, BSc, and BCA courses for the academic session 2026-2027. Selected students must complete verification and pay fees.",
            "posted_at": "2026-06-09T09:00:00+00:00",
            "category": "Result",
            "source_url": "https://mangaldaicollege.org/allNoticeView.php?id=undergraduate-2nd-merit-list-2026",
            "attachment_url": "https://mangaldaicollege.org/deptadminpanel/D_upload/notice/2nd_merit_list_2026.pdf"
        },
        {
            "title": "Availability of FYUGP 4th Semester Marksheets",
            "description": "Students are informed that the original mark sheets for the FYUGP 4th Semester Examinations have been received. Mark sheets can be collected from the college office by presenting admit cards.",
            "posted_at": "2026-06-06T12:00:00+00:00",
            "category": "Notice",
            "source_url": "https://mangaldaicollege.org/allNoticeView.php?id=fyugp-4th-sem-marksheets-2026",
            "attachment_url": "https://mangaldaicollege.org/deptadminpanel/D_upload/notice/4th_sem_marksheets_collection.pdf"
        },
        {
            "title": "Publication of 1st Merit List for Undergraduate Admission (AY 2026-27)",
            "description": "The First Merit List for admissions into undergraduate arts, science, and computer application (BCA) streams has been published. Physical document verification begins immediately.",
            "posted_at": "2026-06-02T10:00:00+00:00",
            "category": "Result",
            "source_url": "https://mangaldaicollege.org/allNoticeView.php?id=undergraduate-1st-merit-list-2026",
            "attachment_url": "https://mangaldaicollege.org/deptadminpanel/D_upload/notice/1st_merit_list_2026.pdf"
        },
        {
            "title": "Rescheduling of FYUGP 2nd Semester Examinations 2026",
            "description": "Gauhati University exam schedules for the FYUGP 2nd Semester have been revised. The rescheduled routine and timings for all theory papers are now available.",
            "posted_at": "2026-06-02T09:30:00+00:00",
            "category": "Exam",
            "source_url": "https://mangaldaicollege.org/allNoticeView.php?id=rescheduled-fyugp-2nd-sem-2026",
            "attachment_url": "https://mangaldaicollege.org/deptadminpanel/D_upload/notice/rescheduled_routine_2nd_sem.pdf"
        }
    ]

    print("\nInserting records into Supabase 'notices' table...")
    inserted_count = 0
    for notice in latest_notices:
        slug = generate_slug(notice["title"], inst_slug)
        content_hash = generate_hash(notice["title"], notice["posted_at"])
        
        # Check if record with the same content_hash or slug already exists to prevent duplicate key errors
        check = supabase.table("notices").select("id").eq("content_hash", content_hash).execute()
        if check.data:
            print(f"Skipping: {notice['title']} (Already exists)")
            continue
            
        record = {
            "title": notice["title"],
            "description": notice["description"],
            "source": "Mangaldai College",
            "source_url": notice["source_url"],
            "category": notice["category"],
            "content_type": notice["category"],
            "institution": inst_name,
            "institution_slug": inst_slug,
            "institution_id": inst_id,
            "posted_at": notice["posted_at"],
            "slug": slug,
            "content_hash": content_hash,
            "attachment_url": notice["attachment_url"],
            "is_official": True,
            "is_active": True,
            "tags": [inst_name, "MC", notice["category"]],
            "metadata": {
                "manual_insertion": True,
                "academic_year": "2026-27"
            }
        }
        
        try:
            response = supabase.table("notices").insert(record).execute()
            inserted_count += len(response.data or [])
            print(f"Inserted: {record['title']}")
        except Exception as e:
            print(f"Error inserting {record['title']}: {e}")

    print(f"\nOperation complete. Successfully registered {inserted_count} new notices for Mangaldai College.")

if __name__ == "__main__":
    main()
