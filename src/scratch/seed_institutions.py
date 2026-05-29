import sys
import os

# Adjust python path to find modules
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from services.supabase_service import supabase

new_institutions = [
    {
        "name": "Darrang College",
        "slug": "darrang-college",
        "description": "A premier co-educational higher education institution located in Tezpur, Sonitpur, Assam.",
        "website": "https://darrangcollege.ac.in",
        "location": "Tezpur, Sonitpur, Assam"
    },
    {
        "name": "Tezpur College",
        "slug": "tezpur-college",
        "description": "An arts and commerce higher education college located in Tezpur, Sonitpur, Assam.",
        "website": "https://tezpurcollege.com",
        "location": "Tezpur, Sonitpur, Assam"
    },
    {
        "name": "LOKD College",
        "slug": "lokd-college",
        "description": "Loknayak Omeo Kumar Das College is a higher education institution located in Dhekiajuli, Sonitpur, Assam.",
        "website": "https://lokdcollege.in",
        "location": "Dhekiajuli, Sonitpur, Assam"
    },
    {
        "name": "Royal Global University",
        "slug": "royal-global-university",
        "description": "A private university established in Guwahati, Assam, offering a wide range of academic programs.",
        "website": "https://rgu.ac",
        "location": "Guwahati, Assam"
    },
    {
        "name": "IGNOU Guwahati Regional Centre",
        "slug": "ignou-guwahati",
        "description": "Guwahati Regional Centre of the Indira Gandhi National Open University (IGNOU) serving student services in Assam.",
        "website": "http://rcguwahati.ignou.ac.in",
        "location": "Guwahati, Assam"
    },
    {
        "name": "Assam Don Bosco University",
        "slug": "don-bosco-university",
        "description": "A private Catholic state university located in Guwahati, Assam, India, established in 2008.",
        "website": "https://dbuniversity.ac.in",
        "location": "Guwahati, Sonapur, Assam"
    },
    {
        "name": "Pandu College",
        "slug": "pandu-college",
        "description": "A prominent co-educational college located in Pandu, Guwahati, Assam, established in 1962.",
        "website": "https://panducollege.ac.in",
        "location": "Guwahati, Assam"
    },
    {
        "name": "Assam Down Town University",
        "slug": "assam-down-town-university",
        "description": "A private university located in Panikhaiti, Guwahati, Assam, India, offering academic courses in diverse streams.",
        "website": "https://adtu.in",
        "location": "Guwahati, Assam"
    }
]

def seed():
    print("Starting seeding of new institutions...")
    for inst in new_institutions:
        try:
            print(f"Upserting {inst['name']}...")
            res = supabase.table("institutions").upsert(inst, on_conflict="slug").execute()
            print(f"Successfully seeded: {inst['name']}")
        except Exception as e:
            print(f"Error seeding {inst['name']}: {e}")

if __name__ == "__main__":
    seed()
