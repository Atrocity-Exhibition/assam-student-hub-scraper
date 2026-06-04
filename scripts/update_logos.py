import os
from dotenv import load_dotenv
from supabase import create_client

# Resolve path to .env in scrapers/ directory
dotenv_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path)

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

if not supabase_url or not supabase_key:
    print("Error: SUPABASE_URL or SUPABASE_KEY not found in environment.")
    exit(1)

supabase = create_client(supabase_url, supabase_key)

updates = {
    "assam-public-service-commission": "/logos/apsc.png",
    "state-level-police-recruitment-board": "/logos/slprb.png",
    "gauhati-university": "/logos/gauhati-university.png",
    "cotton-university": "/logos/cotton-university.png",
    "dibrugarh-university": "/logos/dibrugarh-university.png"
}

for slug, logo_url in updates.items():
    print(f"Updating logo for {slug} to {logo_url}...")
    try:
        res = supabase.table("institutions").update({"logo_url": logo_url}).eq("slug", slug).execute()
        if res.data:
            print(f"  Successfully updated {slug}.")
        else:
            print(f"  Warning: No institution found matching slug {slug}.")
    except Exception as e:
        print(f"  Error updating {slug}: {e}")

print("Done!")
