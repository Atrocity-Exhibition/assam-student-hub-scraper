import sys
import os

# Add src folder to Python path for importing modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from scrapers.gauhati import GauhatiScraper

def test_gauhati_scraper():
    print("=== Launching Gauhati University Scraper Test ===")
    
    scraper = GauhatiScraper()
    items = scraper.run()
    
    print(f"Scraped Items Count: {len(items)}")
    
    assert len(items) > 0, "Error: Scraper returned 0 items from Gauhati University!"
    
    # Inspect and validate structural fields on the first result item
    first_item = items[0]
    print("\nFirst notice inspection details:")
    print(f"  Title:             {first_item.title}")
    print(f"  Source URL:        {first_item.source_url}")
    print(f"  Attachment URL:    {first_item.attachment_url}")
    print(f"  Category:          {first_item.category}")
    print(f"  Institution Slug:  {first_item.institution_slug}")
    print(f"  Posted At:         {first_item.posted_at}")
    print(f"  Generated Slug:    {first_item.slug}")
    print(f"  Tags:              {first_item.tags}")
    print(f"  Metadata:          {first_item.metadata}")
    
    assert first_item.title, "Title should not be blank"
    assert first_item.slug, "Auto slug should be populated"
    assert first_item.source_url.startswith("http"), "Source URL must resolve to absolute URL"
    assert first_item.institution_slug == "gauhati-university", f"Institution slug is invalid: {first_item.institution_slug}"
    assert first_item.category in ["recruitment", "result", "exam", "admission", "scholarship", "notice"], "Category does not match standard options"
    
    print("\n[SUCCESS] Gauhati University checks passed successfully!")

if __name__ == "__main__":
    test_gauhati_scraper()
