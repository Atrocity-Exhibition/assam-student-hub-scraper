# AssamStudentHub — Scrapers (Backend)

A robust Python 3.11 ETL (Extract, Transform, Load) pipeline that automatically scrapes, validates, deduplicates, and ingests notices, recruitment posts, and announcements from 32+ institutions in Assam. 

## Features
* **32+ Custom Crawlers**: Highly optimized parsers built using BeautifulSoup4 targeting:
  * **Recruitment**: APSC, SLPRB, GHC, AESRB, NHM, NCS Portal, NRL.
  * **Universities**: Gauhati, Cotton, Dibrugarh, Tezpur, Bodoland, KKHSOU, AWU, ASTU, Assam University, Royal Global, ADTU, etc.
  * **Boards & Colleges**: SEBA, AHSEC, DHE Assam, Darrang College, Tezpur College, Pandu College, Don Bosco, etc.
  * **Aggregators**: AssamCareer, DailyAssamJob, AllJobAssam, AssamJobNews.
* **Smart Parsing**: Regular expression parser that identifies pay scales, stipends, and age limits from unstructured HTML.
* **Deduplication**: Merges overlapping notice copies across aggregators and official sources using `content_hash` and `reliability_score`.
* **Telemetry**: Logs execution times, status flags, and error tracebacks to the Supabase database. These logs are displayed in real-time on the frontend `/monitoring` page.

## Automation & GitHub Actions
The scrapers are fully automated via GitHub Actions cron workflows. They are split into three scheduling tiers to respect server rate limits and prioritize urgent notices:

- `scrape-fast.yml`: Runs every **6 hours** (High-priority jobs and recruitment).
- `scrape-medium.yml`: Runs every **12 hours** (Standard academic institutions).
- `scrape-slow.yml`: Runs every **24 hours** (Heavy archives and legacy systems).

## Environment Variables
Create a `.env` file before running the CLI locally:

```env
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_service_role_key
DISCORD_WEBHOOK_URL=your_discord_alerts_webhook
```

## Local CLI Usage

```bash
# Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run a specific scraper
python src/main.py --scraper apsc

# Run with a record limit (useful for testing)
python src/main.py --scraper dibrugarh --limit 10

# Test without inserting into the database
python src/main.py --scraper cotton --dry-run

# Run all scrapers in a specific schedule tier
python src/main.py --frequency 6h
```
