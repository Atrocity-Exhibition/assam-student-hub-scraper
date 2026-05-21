#!/bin/bash
# run_scrapers.sh - Entrypoint script for scheduled systemd timers to run groups of scrapers
# Sets up path, virtual environment, and executes selected scraper groups sequentially.

# Get current script directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( dirname "$DIR" )"

cd "$PROJECT_DIR" || exit 1

# Activate virtualenv
if [ -d "venv" ]; then
    source venv/bin/activate
fi

GROUP=$1

case "$GROUP" in
    fast)
        echo "Running fast frequency scrapers (SLPRB, APSC)..."
        python src/main.py --scraper slprb
        python src/main.py --scraper apsc
        ;;
    medium)
        echo "Running medium frequency scrapers (Dibrugarh)..."
        python src/main.py --scraper dibrugarh
        ;;
    slow)
        echo "Running slow frequency scrapers (Gauhati, Cotton)..."
        python src/main.py --scraper gauhati
        python src/main.py --scraper cotton
        ;;
    daily)
        echo "Running daily frequency scrapers (Assam Career, Daily Assam Job, NHM Assam, AESRB, NCS Portal, Tezpur, Bodoland, Mangaldai, AHSEC, SEBA)..."
        python src/main.py --scraper assam_career
        python src/main.py --scraper daily_assam_job
        python src/main.py --scraper nhm_assam
        python src/main.py --scraper aesrb
        python src/main.py --scraper ncs_portal
        python src/main.py --scraper tezpur
        python src/main.py --scraper bodoland
        python src/main.py --scraper mangaldai
        python src/main.py --scraper ahsec
        python src/main.py --scraper seba
        ;;
    *)
        echo "Usage: $0 {fast|medium|slow|daily}"
        exit 1
        ;;
esac
