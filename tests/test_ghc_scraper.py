import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from scrapers.ghc import GHCScraper

def test_ghc_scraper():
    print("=== Launching GHC Scraper Test ===")
    
    scraper = GHCScraper()
    items = scraper.run()
    
    print(f"Scraped Items Count: {len(items)}")
    assert len(items) > 0, "Error: Scraper returned 0 items from Gauhati High Court!"
    
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
    assert first_item.institution_slug == "gauhati-high-court", "Institution slug is invalid"
    assert first_item.reliability_score == 10, "Reliability score should be 10 for government board"
    assert len(first_item.content_hash) == 64, "Content hash should be SHA-256 (64 hex characters)"
    
    print("\n[SUCCESS] GHC scraper verification checks passed successfully!")

if __name__ == "__main__":
    test_ghc_scraper()
