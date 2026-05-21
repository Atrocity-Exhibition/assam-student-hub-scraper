import traceback
import time
from datetime import datetime, timezone
import logging
from typing import Optional, List
from services.supabase_service import supabase

logger = logging.getLogger("services.monitor")

class ScraperRunTracker:
    def __init__(self, scraper_name: str):
        self.scraper_name = scraper_name
        self.run_id: Optional[int] = None
        self.start_time: Optional[float] = None
        self.started_at: Optional[datetime] = None
        self.items_scraped = 0
        self.items_inserted = 0
        self.items_updated = 0
        self.errors: List[str] = []
        self.traceback: Optional[str] = None

    def __enter__(self):
        self.start_time = time.time()
        self.started_at = datetime.now(timezone.utc)
        
        try:
            # Create a run record in the database with status 'running'
            response = supabase.table("scraper_runs").insert({
                "scraper_name": self.scraper_name,
                "status": "running",
                "started_at": self.started_at.isoformat(),
            }).execute()
            
            if response.data:
                self.run_id = response.data[0]["id"]
                logger.info(f"Scraper Run '{self.scraper_name}' initialized with Run ID: {self.run_id}")
            else:
                logger.error("Failed to initialize scraper run tracking in DB: empty response data.")
        except Exception as e:
            logger.error(f"Failed to insert running status into scraper_runs table: {e}")
            
        return self

    def add_error(self, error_msg: str):
        self.errors.append(error_msg)
        logger.error(f"Scraper Run Error: {error_msg}")

    def set_counts(self, scraped: int, inserted: int, updated: int):
        self.items_scraped = scraped
        self.items_inserted = inserted
        self.items_updated = updated

    def send_discord_alert(self, alert_type: str, message: str, details: Optional[str] = None):
        """
        Sends an alert notification embed to the configured Discord channel webhook.
        """
        from config.settings import DISCORD_WEBHOOK_URL
        if not DISCORD_WEBHOOK_URL:
            logger.warning("DISCORD_WEBHOOK_URL is not set. Skipping Discord alert.")
            return

        color = 16711680  # Red for failures
        title = f"🚨 Scraper Failure: {self.scraper_name}"
        if alert_type == "empty":
            color = 16753920  # Orange for zero yield
            title = f"⚠️ Scraper Empty Yield: {self.scraper_name}"
        elif alert_type == "anomaly":
            color = 16776960  # Yellow for low yield anomaly
            title = f"⚠️ Scraper Low Yield Anomaly: {self.scraper_name}"

        embed = {
            "title": title,
            "description": message,
            "color": color,
            "fields": [],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        if details:
            embed["fields"].append({
                "name": "Alert Details",
                "value": details[:1024],  # Discord limits field values to 1024 characters
                "inline": False
            })

        payload = {"embeds": [embed]}

        try:
            import requests
            response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
            if response.status_code != 204:
                logger.error(f"Failed to send Discord alert: status code {response.status_code}, response: {response.text}")
            else:
                logger.info(f"Discord alert sent successfully: {title}")
        except Exception as e:
            logger.error(f"Failed to post Discord alert: {e}")

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Calculate duration
        end_time = time.time()
        duration_seconds = int(end_time - self.start_time) if self.start_time else 0
        completed_at = datetime.now(timezone.utc)

        status = "completed"
        if exc_type is not None:
            status = "failed"
            # Format and save traceback string
            self.traceback = "".join(traceback.format_exception(exc_type, exc_val, exc_tb))
            self.add_error(str(exc_val))
            logger.error(f"Scraper Run '{self.scraper_name}' failed with exception: {exc_val}")
        elif len(self.errors) > 0:
            status = "failed"

        if not self.run_id:
            logger.warning("Scraper Run Tracker exit: No run_id available to update in database.")
            return False  # Let exception propagate if there was one

        try:
            # Prepare update payloads
            update_data = {
                "status": status,
                "completed_at": completed_at.isoformat(),
                "duration_seconds": duration_seconds,
                "items_scraped": self.items_scraped,
                "items_inserted": self.items_inserted,
                "items_updated": self.items_updated,
                "errors": self.errors
            }
            if self.traceback:
                update_data["traceback"] = self.traceback

            supabase.table("scraper_runs").update(update_data).eq("id", self.run_id).execute()
            logger.info(
                f"Scraper Run '{self.scraper_name}' finished. Status: {status}. "
                f"Scraped: {self.items_scraped}, Inserted: {self.items_inserted}, Updated: {self.items_updated}, "
                f"Duration: {duration_seconds}s"
            )

            # Perform health checks and alerting based on final run status and counts
            if status == "failed":
                # Check for 3 consecutive failures
                try:
                    res = supabase.table("scraper_runs").select("status, started_at").eq("scraper_name", self.scraper_name).order("started_at", desc=True).limit(3).execute()
                    if res.data and len(res.data) >= 3:
                        statuses = [run["status"] for run in res.data]
                        if all(s == "failed" for s in statuses):
                            history = "\n".join([f"- Run started at {run['started_at']}: {run['status']}" for run in res.data])
                            msg = f"The scraper `{self.scraper_name}` has failed for 3 consecutive runs."
                            err_desc = self.errors[-1] if self.errors else "Unknown error"
                            self.send_discord_alert(
                                alert_type="failure",
                                message=msg,
                                details=f"Recent execution history:\n{history}\n\nLatest Error Details:\n{err_desc}"
                            )
                except Exception as alert_err:
                    logger.error(f"Failed during consecutive failure alert check: {alert_err}")

            elif status == "completed":
                if self.items_scraped == 0:
                    # Check for 3 consecutive completed runs with 0 items scraped (empty pages check)
                    try:
                        res = supabase.table("scraper_runs").select("items_scraped, status, started_at").eq("scraper_name", self.scraper_name).order("started_at", desc=True).limit(3).execute()
                        if res.data and len(res.data) >= 3:
                            counts = [run["items_scraped"] for run in res.data]
                            if all(c == 0 for c in counts):
                                history = "\n".join([f"- Run started at {run['started_at']}: {run['items_scraped']} items ({run['status']})" for run in res.data])
                                msg = f"The scraper `{self.scraper_name}` has yielded 0 scraped items for 3 consecutive runs. This indicates selectors may have broken due to layout changes."
                                self.send_discord_alert(
                                    alert_type="empty",
                                    message=msg,
                                    details=f"Recent execution yields:\n{history}"
                                )
                    except Exception as alert_err:
                        logger.error(f"Failed during consecutive empty yield check: {alert_err}")
                else:
                    # Perform anomaly detection (yield dropped below 20% of historical average)
                    try:
                        res = supabase.table("scraper_runs").select("id, items_scraped").eq("scraper_name", self.scraper_name).eq("status", "completed").gt("items_scraped", 0).order("started_at", desc=True).limit(11).execute()
                        if res.data:
                            past_counts = [run["items_scraped"] for run in res.data if run["id"] != self.run_id][:10]
                            if len(past_counts) >= 3:
                                avg_count = sum(past_counts) / len(past_counts)
                                if self.items_scraped < avg_count * 0.2:
                                    msg = f"Potential partial selector failure detected for `{self.scraper_name}`. Current run scraped only {self.items_scraped} items, which is less than 20% of the historical average of the last {len(past_counts)} successful runs ({avg_count:.1f} items)."
                                    self.send_discord_alert(
                                        alert_type="anomaly",
                                        message=msg,
                                        details=f"Current Yield: {self.items_scraped} items\nHistorical Average: {avg_count:.1f} items\nRecent yields: {past_counts}"
                                    )
                    except Exception as alert_err:
                        logger.error(f"Failed during yield anomaly check: {alert_err}")

        except Exception as e:
            logger.error(f"Failed to update scraper run final status or process alerts: {e}")

        return False  # Let exception propagate if there was one

