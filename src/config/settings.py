from dotenv import load_dotenv
import os

# Load environment variables from .env
load_dotenv()

# Supabase Credentials
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Discord Webhook for Alerts
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")


# Scraper Polite/Rate Limiting Configurations
REQUEST_DELAY = float(os.getenv("REQUEST_DELAY", "2.0"))     # Delay in seconds between requests
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "15"))    # Request timeout in seconds
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))            # Max retries on request failure

# Logging Config
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Default request headers mimicking a desktop browser to prevent user-agent blocks
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive"
}
