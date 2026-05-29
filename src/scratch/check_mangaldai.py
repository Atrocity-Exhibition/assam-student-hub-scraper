import requests
from bs4 import BeautifulSoup

url = "https://mangaldaicollege.org/allNoticeView.php"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

try:
    print(f"Fetching {url}...")
    response = requests.get(url, headers=headers, verify=False, timeout=10)
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Print out any tables
    tables = soup.find_all("table")
    print(f"\nFound {len(tables)} tables.")
    for idx, table in enumerate(tables):
        print(f"\n--- Table {idx+1} ---")
        rows = table.find_all("tr")
        print(f"Rows count: {len(rows)}")
        for r_idx, r in enumerate(rows[:5]):
            print(f"Row {r_idx+1}: {r.get_text().strip().replace('\n', ' | ')[:150]}")
            
    # Also find all links pointing to drive or PDFs or uploads
    print("\nLinks containing uploads or PDF:")
    count = 0
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        text = a.get_text().strip()
        if "upload" in href.lower() or href.lower().endswith(".pdf") or "drive.google" in href.lower():
            print(f"{count+1}. Text: '{text}' | Href: '{href}'")
            count += 1
            if count >= 30:
                break
except Exception as e:
    print(f"Error: {e}")
