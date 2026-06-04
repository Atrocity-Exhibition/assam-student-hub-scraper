import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

targets = {
    "apsc": "https://apsc.nic.in",
    "cotton": "https://cottonuniversity.ac.in",
    "gauhati": "https://gauhati.ac.in",
    "dibrugarh": "https://dibru.ac.in"
}

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

for name, url in targets.items():
    print(f"Scraping {name} ({url})...")
    try:
        r = requests.get(url, headers=headers, timeout=15, verify=False)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            # Look for img tags with "logo" in src, class, or id
            imgs = soup.find_all('img')
            found = []
            for img in imgs:
                src = img.get('src', '')
                alt = img.get('alt', '')
                img_class = str(img.get('class', ''))
                img_id = img.get('id', '')
                
                if 'logo' in src.lower() or 'logo' in alt.lower() or 'logo' in img_class.lower() or 'logo' in img_id.lower() or 'seal' in src.lower():
                    abs_src = urljoin(url, src)
                    found.append((abs_src, alt))
            
            if found:
                print(f"  Found potential logos for {name}:")
                for src, alt in found:
                    print(f"    - URL: {src} (Alt: '{alt}')")
            else:
                # print first 3 images if no logo match
                print(f"  No explicit logo class/alt match. First 3 images on page:")
                for img in imgs[:3]:
                    print(f"    - URL: {urljoin(url, img.get('src', ''))}")
        else:
            print(f"  Failed with status code {r.status_code}")
    except Exception as e:
        print(f"  Error: {e}")
