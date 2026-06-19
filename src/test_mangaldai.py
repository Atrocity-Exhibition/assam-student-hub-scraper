import httpx
from bs4 import BeautifulSoup
import re

url = "https://mangaldaicollege.org/allNoticeView.php"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive"
}

print(f"Fetching {url}...")
try:
    # Use httpx with custom headers and verify=False
    response = httpx.get(url, headers=headers, verify=False, timeout=15)
    print(f"Response status: {response.status_code}")
    
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Let's find notice items
    message_bodies = soup.find_all(class_="message-body")
    print(f"Found {len(message_bodies)} notice containers.")
    
    for i, msg_body in enumerate(message_bodies[:25]):
        a = msg_body.find_parent("a")
        href = a.get("href", "").strip() if a else "No link parent"
        title_el = msg_body.find("h5")
        title = title_el.get_text().strip() if title_el else "No title"
        span_el = msg_body.find("span")
        posted_text = span_el.get_text().strip() if span_el else "No date span"
        
        print(f"#{i+1}: {title}")
        print(f"    Date: {posted_text}")
        print(f"    Link: {href}")
        print("-" * 60)
except Exception as e:
    print(f"Error fetching/parsing: {e}")
