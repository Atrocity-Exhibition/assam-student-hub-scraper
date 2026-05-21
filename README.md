# AssamStudentHub — Scrapers

Python-based web scraping pipeline that aggregates notices, job postings, and announcements from Assam government bodies and universities. Scraped data is validated, deduplicated, and bulk-upserted into a Supabase database to power the [AssamStudentHub](https://github.com/rahulv-official/assam-student-hub) frontend.

---

## Sources

| Scraper key       | Source                                          |
|-------------------|-------------------------------------------------|
| `apsc`            | Assam Public Service Commission                 |
| `slprb`           | Assam State Level Police Recruitment Board      |
| `gauhati`         | Gauhati University                              |
| `cotton`          | Cotton University                               |
| `dibrugarh`       | Dibrugarh University                            |
| `tezpur`          | Tezpur University                               |
| `bodoland`        | Bodoland University                             |
| `mangaldai`       | Mangaldai College                               |
| `ahsec`           | Assam Higher Secondary Education Council        |
| `seba`            | Board of Secondary Education, Assam             |
| `nhm_assam`       | National Health Mission Assam                   |
| `aesrb`           | Assam Electronic Service Recruitment Board      |
| `ncs_portal`      | National Career Service Portal (Assam)          |
| `assam_career`    | AssamCareer.in                                  |
| `daily_assam_job` | DailyAssamJob.in                                |

---

## Setup

```bash
# Clone and enter the project
git clone https://github.com/rahulv-official/assam-student-hub-scrapers
cd assam-student-hub-scrapers

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Fill in your Supabase URL and anon key
```

---

## Usage

### Run a single scraper

```bash
python src/main.py --scraper apsc
```

### Dry run (no database writes)

```bash
python src/main.py --scraper gauhati --dry-run
```

### Limit records processed

```bash
python src/main.py --scraper dibrugarh --limit 10
```

### Run by frequency group

```bash
# fast  → slprb, apsc
# medium → dibrugarh
# slow  → gauhati, cotton
# daily → all remaining sources

bash src/run_scrapers.sh daily
```

---

## Environment Variables

| Variable                    | Description               |
|-----------------------------|---------------------------|
| `SUPABASE_URL`              | Your Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key |

---

## Stack

- **Python 3** — scraping & data pipeline
- **BeautifulSoup4 + httpx** — HTML parsing & HTTP requests
- **Pydantic** — notice schema validation
- **Supabase** — data storage & upsert
- **python-dotenv** — environment config
