# AssamStudentHub — Scrapers

A Python-based ETL (Extract, Transform, Load) pipeline that automatically scrapes, validates, deduplicates, and ingests notices, recruitment posts, exam notifications, and results from 25+ government bodies, recruitment boards, and academic institutions in Assam. 

The collected data is uploaded to a central Supabase instance to feed the [AssamStudentHub Frontend](https://github.com/rahulv-official/assam-student-hub).

---

## Core Features

* **25+ Custom Crawlers**: Highly optimized parsers built using BeautifulSoup4 and HTTPX targeting:
  * **Recruitment Boards**: Assam Public Service Commission (`apsc`), State Level Police Recruitment Board (`slprb`), GHC, AESRB, NHM.
  * **Universities**: Gauhati University, Cotton University, Dibrugarh University, Tezpur University, Bodoland University, KKHSOU, AWU, ASTU, Assam University.
  * **School & Higher Education Boards**: SEBA, AHSEC.
* **Intelligent Salary and Pay Extraction**: Regular expression parser that identifies pay scales, stipends, and consolidated salaries from unstructured notification texts.
* **Robust Schema Validation**: Pydantic schemas validating fields, timestamps, categories, slugs, and attachments to ensure strict data quality.
* **Reliability-Based Deduplication**: Merges overlapping notice copies across aggregators and official sources using `content_hash` and source priority rankings (`reliability_score`).
* **Active Telemetry Tracking**: Logs run timings, status flags (`running`, `completed`, `failed`), scrape count statistics, and error tracebacks to the database. These logs are displayed in real-time on the frontend `/monitoring` page.
* **Flexible CLI and Scheduling Groups**: Supports running specific scrapers, dry runs, record limits, and batch groups (fast, medium, slow, daily) perfect for cron or systemd automation.

---

## Getting Started

### Prerequisites

* Python 3.10 or later
* Access credentials for a Supabase database instance

### 1. Installation

Clone the repository and enter the directory:

```bash
git clone https://github.com/rahulv-official/assam-student-hub-scrapers
cd assam-student-hub-scrapers
```

Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

Install the required python libraries:

```bash
pip install -r requirements.txt
```

### 2. Configuration

Create a `.env` file in the root directory:

```env
SUPABASE_URL=your_supabase_project_url
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
```

---

## Usage CLI

### Run a Single Scraper

Execute a scraper and ingest its records directly into the database:

```bash
python src/main.py --scraper apsc
```

### Dry Run Mode

Verify HTML parsing and data extraction locally without writing any changes to the database:

```bash
python src/main.py --scraper gauhati --dry-run
```

### Apply Record Limit

Restrict the scraper to process a limited number of records (useful for debugging or initial testing):

```bash
python src/main.py --scraper dibrugarh --limit 10
```

### Run by Frequency Group

Execute a batch of scrapers grouped together by their update schedules:

```bash
# fast   -> slprb, apsc, ghc (highly active recruitment boards)
# medium -> dibrugarh, nhm_assam, aesrb, assam_university, astu, kkhsou, awu, nrl
# slow   -> gauhati, cotton (heavy university notice archives)
# daily  -> all remaining sources

bash src/run_scrapers.sh daily
```

---

## Project Structure

```
src/
├── config/              # Scraper scheduling schedules & API options
├── models/              # Pydantic schemas enforcing structural rules (ScrapedItem)
├── scrapers/            # Individual python scrapers inheriting from BaseScraper
│   ├── base_scraper.py  # Base abstract class managing HTTP, retries, and delay limits
│   └── cotton.py, etc.  # Site-specific scraping implementations
├── services/            # Supabase database helpers & telemetric logs
│   ├── supabase_service.py # Core upsert, check, and merge functions
│   └── monitor_service.py  # Context-managed logging tracking scraper runs
├── utils/               # Text normalizers, dates, and title cleaners
└── main.py              # Central entry point parsing command line arguments
```

---

## License

This project is licensed under the MIT License.
