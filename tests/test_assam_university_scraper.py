import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from scrapers.assam_university import AssamUniversityScraper

def test_assam_university_scraper():
    print("=== Launching Assam University Scraper Test ===")
    
    scraper = AssamUniversityScraper()
    items = scraper.run()
    
    print(f"Scraped Items Count: {len(items)}")
    assert len(items) > 0, "Error: Scraper returned 0 items from Assam University!"
    
    first_item = items[0]
    print("\nFirst notice inspection details:")
    print(f"  Title:             {first_item.title}")
    print(f"  Source URL:        {first_item.source_url}")
    print(f"  Category:          {first_item.category}")
    print(f"  Institution Slug:  {first_item.institution_slug}")
    print(f"  Posted At:         {first_item.posted_at}")
    print(f"  Generated Slug:    {first_item.slug}")
    print(f"  Reliability Score: {first_item.reliability_score}")
    print(f"  Canonical URL:    {first_item.canonical_url}")
    print(f"  Content Hash:     {first_item.content_hash}")
    
    # Assertions
    assert first_item.title, "Title should not be blank"
    assert first_item.slug, "Auto slug should be populated"
    assert first_item.source_url.startswith("http"), "Source URL must resolve to absolute HTTP URL"
    assert first_item.canonical_url.startswith("http"), "Canonical URL must resolve to absolute HTTP URL"
    assert first_item.institution_slug == "assam-university-silchar", "Institution slug is invalid"
    assert first_item.reliability_score == 10, "Reliability score should be 10 for university"
    assert len(first_item.content_hash) == 64, "Content hash should be SHA-256 (64 hex characters)"
    
    print("\n[SUCCESS] Assam University scraper verification checks passed successfully!")

if __name__ == "__main__":
    test_assam_university_scraper()
