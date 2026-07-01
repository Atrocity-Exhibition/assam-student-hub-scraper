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
    print("Fetching top 15 latest notices by posted_at...")
    response = supabase.table("notices").select("id, title, posted_at, created_at, institution, category").order("posted_at", desc=True).limit(15).execute()
    
    for i, n in enumerate(response.data or []):
        print(f"#{i+1}: {n['title']}")
        print(f"    Posted: {n['posted_at']} | Created: {n['created_at']}")
        print(f"    Institution: {n['institution']} | Category: {n['category']}")
        print("-" * 60)

if __name__ == "__main__":
    main()
