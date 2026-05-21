import sys
import os

# Add src folder to Python path for importing modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from scrapers.slprb import SLPRBScraper

def test_slprb_scraper():
    print("=== Launching SLPRB Scraper Test ===")
    
    # Initialize the scraper
    scraper = SLPRBScraper()
    
    # Run the full scraping + validation pipeline
    items = scraper.run()
    
    print(f"Scraped Items Count: {len(items)}")
    
    # Assert that data was retrieved
    assert len(items) > 0, "Error: Scraper returned 0 items from SLPRB!"
    
    # Inspect and validate structural fields on the first result item
    first_item = items[0]
    print("\nFirst notice inspection details:")
    print(f"  Title:             {first_item.title}")
    print(f"  Source URL:        {first_item.source_url}")
    print(f"  Category:          {first_item.category}")
    print(f"  Institution Slug:  {first_item.institution_slug}")
    print(f"  Posted At:         {first_item.posted_at}")
    print(f"  Generated Slug:    {first_item.slug}")
    print(f"  Tags:              {first_item.tags}")
    print(f"  Metadata:          {first_item.metadata}")
    print(f"  Snapshot length:   {len(first_item.raw_html) if first_item.raw_html else 0} characters")
    
    # Quality control assertions
    assert first_item.title, "Title should not be blank"
    assert first_item.slug, "Auto slug should be populated"
    assert first_item.source_url.startswith("http"), "Source URL must resolve to absolute HTTP URL"
    assert first_item.institution_slug == "state-level-police-recruitment-board", "Institution slug is invalid"
    assert first_item.category in ["recruitment", "result", "exam", "admission", "scholarship", "notice"], "Category does not match standard options"
    
    print("\n[SUCCESS] All basic SLPRB structure checks passed successfully!")

if __name__ == "__main__":
    test_slprb_scraper()
