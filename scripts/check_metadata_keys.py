import urllib.request
import json

url = "https://qktomyipkzgdlexhkuqr.supabase.co/rest/v1/notices?select=id,title,category,metadata&limit=1000"
headers = {
    "apikey": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFrdG9teWlwa3pnZGxleGhrdXFyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzkxNzUwMjQsImV4cCI6MjA5NDc1MTAyNH0.tqINFXcp52nPIqSCDYs-PfCEIYrv4VqbJf2-JTBlCMI",
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFrdG9teWlwa3pnZGxleGhrdXFyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzkxNzUwMjQsImV4cCI6MjA5NDc1MTAyNH0.tqINFXcp52nPIqSCDYs-PfCEIYrv4VqbJf2-JTBlCMI"
}

req = urllib.request.Request(url, headers=headers)
try:
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode('utf-8'))
        print(f"Retrieved {len(data)} notices.")
        all_keys = set()
        notices_with_keys = {}
        for item in data:
            meta = item.get("metadata")
            if meta:
                for k, v in meta.items():
                    all_keys.add(k)
                    if k not in notices_with_keys:
                        notices_with_keys[k] = []
                    if len(notices_with_keys[k]) < 3:
                        notices_with_keys[k].append((item['id'], item['title'][:50], v))
        print("All unique metadata keys:", all_keys)
        for k, examples in notices_with_keys.items():
            print(f"\nKey: {k}")
            for ex in examples:
                print(f"  Notice ID {ex[0]}: {ex[1]} -> {ex[2]}")
except Exception as e:
    print("Error:", e)
