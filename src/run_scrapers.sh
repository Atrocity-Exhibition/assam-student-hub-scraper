#!/bin/bash
# run_scrapers.sh - Entrypoint script for scheduled systemd timers to run groups of scrapers
# Sets up path, virtual environment, and executes selected scraper groups dynamically.

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
        echo "Running 6h (fast) frequency scrapers dynamically..."
        python src/main.py --frequency 6h
        ;;
    medium)
        echo "Running 12h (medium) frequency scrapers dynamically..."
        python src/main.py --frequency 12h
        ;;
    slow|daily)
        echo "Running 24h (slow/daily) frequency scrapers dynamically..."
        python src/main.py --frequency 24h
        ;;
    *)
        echo "Usage: $0 {fast|medium|slow|daily}"
        exit 1
        ;;
esac
