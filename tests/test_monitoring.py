import sys
import os
import time

# Add src folder to Python path for importing modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from services.monitor_service import ScraperRunTracker
from services.supabase_service import supabase

def test_monitoring_success():
    print("\n--- Test 1: Successful Scraper Run Monitoring ---")
    scraper_name = "test_monitoring_success_scraper"
    
    with ScraperRunTracker(scraper_name) as tracker:
        assert tracker.run_id is not None, "Error: run_id was not populated"
        print(f"[PASSED] Scraper run initialized with run_id={tracker.run_id}")
        
        # Verify run is registered in DB as 'running'
        run_record = supabase.table("scraper_runs").select("*").eq("id", tracker.run_id).execute()
        assert len(run_record.data) == 1, "Error: Run record not found in database"
        assert run_record.data[0]["status"] == "running", f"Error: Run status is not 'running', got: {run_record.data[0]['status']}"
        print("[PASSED] Run status is correctly recorded as 'running' inside the context")
        
        # Simulate scraping some pages and updating the count
        time.sleep(1)  # sleep 1s to guarantee duration_seconds >= 1
        tracker.set_counts(scraped=10, inserted=8, updated=2)

    # Verify final status in DB
    run_record = supabase.table("scraper_runs").select("*").eq("id", tracker.run_id).execute()
    data = run_record.data[0]
    
    assert data["status"] == "completed", f"Error: Expected 'completed', got '{data['status']}'"
    assert data["duration_seconds"] >= 1, f"Error: Expected duration >= 1, got {data['duration_seconds']}"
    assert data["items_scraped"] == 10
    assert data["items_inserted"] == 8
    assert data["items_updated"] == 2
    assert not data["errors"], f"Error: Expected no errors, got {data['errors']}"
    assert not data["traceback"], "Error: Expected no traceback"
    
    print("[PASSED] Successful run completed and updated correctly in database.")
    print(f"         Status: {data['status']}, Duration: {data['duration_seconds']}s, "
          f"Scraped: {data['items_scraped']}, Inserted: {data['items_inserted']}, Updated: {data['items_updated']}")


def test_monitoring_failure():
    print("\n--- Test 2: Failed Scraper Run Monitoring with Traceback ---")
    scraper_name = "test_monitoring_failed_scraper"
    run_id = None
    
    try:
        with ScraperRunTracker(scraper_name) as tracker:
            run_id = tracker.run_id
            print(f"[PASSED] Scraper run initialized with run_id={run_id}")
            
            # Force an exception to test traceback capture
            raise ValueError("Simulated Scraper Fail Error for Testing")
    except ValueError as e:
        print(f"[PASSED] Caught expected exception: {e}")
        
    assert run_id is not None, "Error: run_id was never initialized"
    
    # Verify final failed status in DB
    run_record = supabase.table("scraper_runs").select("*").eq("id", run_id).execute()
    data = run_record.data[0]
    
    assert data["status"] == "failed", f"Error: Expected 'failed', got '{data['status']}'"
    assert len(data["errors"]) > 0, "Error: Expected error message to be recorded"
    assert "Simulated Scraper Fail Error for Testing" in data["errors"][0], f"Error: Expected 'Simulated Scraper Fail Error for Testing' in errors, got: {data['errors']}"
    assert data["traceback"] is not None, "Error: Expected traceback to be recorded"
    assert "ValueError" in data["traceback"], "Error: Expected ValueError in traceback"
    assert "test_monitoring_failure" in data["traceback"], "Error: Expected function name in traceback"
    
    print("[PASSED] Failed run caught, logged error messages, and stored Python traceback.")
    print(f"         Status: {data['status']}, Error details: {data['errors']}")
    print(f"         Traceback excerpt:\n{data['traceback'][:150]}...")


if __name__ == "__main__":
    print("=== Launching Scraper Monitoring Test Suite ===")
    test_monitoring_success()
    test_monitoring_failure()
    print("\n[SUCCESS] Monitoring test suite completed successfully!")
