# dashboard.py - Scrapers Platform Observability Dashboard

import argparse
import sys
from datetime import datetime, timezone
import dateutil.parser

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.align import Align

from services.supabase_service import supabase
from config.scrapers_config import SCRAPER_CONFIG

def format_relative_time(dt_str: str) -> str:
    """Format an ISO datetime string into relative time (e.g. 2h 15m ago)."""
    if not dt_str:
        return "N/A"
    try:
        dt = dateutil.parser.parse(dt_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        diff = datetime.now(timezone.utc) - dt
        seconds = int(diff.total_seconds())
        if seconds < 0:
            return "Just now"
        if seconds < 60:
            return f"{seconds}s ago"
        minutes = seconds // 60
        if minutes < 60:
            return f"{minutes}m ago"
        hours = minutes // 60
        if hours < 24:
            return f"{hours}h {minutes % 60}m ago"
        days = hours // 24
        return f"{days}d ago"
    except Exception:
        return "N/A"

def get_status_style(status: str) -> str:
    """Get color style tags for scraper run status."""
    status = status.lower()
    if status == "completed":
        return "[bold green]PASS[/bold green]"
    elif status == "failed":
        return "[bold red]FAIL[/bold red]"
    elif status == "running":
        return "[bold yellow]RUNNING[/bold yellow]"
    else:
        return "[grey50]N/A[/grey50]"

def get_success_rate_style(rate: float) -> str:
    """Colorize success rate based on threshold."""
    if rate >= 90.0:
        return f"[bold green]{rate:.1f}%[/bold green]"
    elif rate >= 75.0:
        return f"[bold yellow]{rate:.1f}%[/bold yellow]"
    else:
        return f"[bold red]{rate:.1f}%[/bold red]"

def render_dashboard(console: Console):
    """Fetch history, compute stats, and render the global status table."""
    try:
        # Fetch the last 500 scraper runs to compute fresh metrics
        response = supabase.table("scraper_runs").select("*").order("started_at", desc=True).limit(500).execute()
        runs = response.data or []
    except Exception as e:
        console.print(f"[bold red]Failed to fetch metrics from Supabase database: {e}[/bold red]")
        return

    # Group runs by scraper
    runs_by_scraper = {}
    for run in runs:
        name = run["scraper_name"]
        if name not in runs_by_scraper:
            runs_by_scraper[name] = []
        runs_by_scraper[name].append(run)

    # Title Banner
    title = Text("AssamStudentHub — Scraper Ingestion Observability", style="bold cyan")
    console.print(Panel(Align.center(title), border_style="cyan"))

    # Table Setup
    table = Table(show_header=True, header_style="bold magenta", box=None)
    table.add_column("Scraper Key", width=18)
    table.add_column("Status", width=10, justify="center")
    table.add_column("Last Executed", width=16)
    table.add_column("Scraped", width=8, justify="right")
    table.add_column("Inserted", width=8, justify="right")
    table.add_column("Duplicates", width=10, justify="right")
    table.add_column("Avg Duration", width=12, justify="right")
    table.add_column("Success Rate", width=12, justify="right")
    table.add_column("Recent Error Message", width=40, overflow="ellipsis")

    # Populate rows for all registered scrapers in registry
    for name in sorted(SCRAPER_CONFIG.keys()):
        scraper_runs = runs_by_scraper.get(name, [])
        
        if not scraper_runs:
            table.add_row(
                name,
                get_status_style("N/A"),
                "Never",
                "0",
                "0",
                "0",
                "0s",
                "N/A",
                "-"
            )
            continue

        last_run = scraper_runs[0]
        status = last_run["status"]
        last_executed = format_relative_time(last_run["started_at"])
        
        scraped = str(last_run.get("items_scraped", 0))
        inserted = str(last_run.get("items_inserted", 0))
        # Duplicates/Updates
        duplicates = str(last_run.get("items_updated", 0))
        
        # Calculate average duration
        durations = [r["duration_seconds"] for r in scraper_runs if r.get("duration_seconds") is not None]
        avg_dur = f"{int(sum(durations) / len(durations))}s" if durations else "0s"
        
        # Calculate success rate
        completed = sum(1 for r in scraper_runs if r["status"] == "completed")
        success_rate = (completed / len(scraper_runs)) * 100.0
        success_str = get_success_rate_style(success_rate)
        
        # Extract recent error if failed
        err_msg = "-"
        if last_run.get("errors"):
            err_msg = last_run["errors"][0]
        elif last_run.get("status") == "failed":
            err_msg = "Scraper process crashed"

        table.add_row(
            name,
            get_status_style(status),
            last_executed,
            scraped,
            inserted,
            duplicates,
            avg_dur,
            success_str,
            err_msg
        )

    console.print(table)
    console.print(f"\n[grey50]Last updated: {datetime.now(timezone.utc).isoformat()} UTC[/grey50]")

def render_inspect(console: Console, name: str):
    """Render detailed execution runs and failure logs for a specific scraper."""
    if name not in SCRAPER_CONFIG:
        console.print(f"[bold red]Error: Scraper '{name}' is not registered in the system config.[/bold red]")
        return

    console.print(Panel(Align.center(Text(f"Scraper Run Logs Inspection: {name}", style="bold yellow")), border_style="yellow"))

    try:
        response = supabase.table("scraper_runs").select("*").eq("scraper_name", name).order("started_at", desc=True).limit(15).execute()
        runs = response.data or []
    except Exception as e:
        console.print(f"[bold red]Failed to fetch logs for {name}: {e}[/bold red]")
        return

    if not runs:
        console.print(f"[yellow]No historical run logs found for scraper '{name}'.[/yellow]")
        return

    table = Table(show_header=True, header_style="bold yellow", box=None)
    table.add_column("Run ID", width=8, justify="right")
    table.add_column("Started At (UTC)", width=24)
    table.add_column("Status", width=10, justify="center")
    table.add_column("Duration", width=10, justify="right")
    table.add_column("Scraped", width=8, justify="right")
    table.add_column("Inserted", width=8, justify="right")
    table.add_column("Updated", width=8, justify="right")
    table.add_column("First Error Message", width=50)

    for run in runs:
        dur = f"{run['duration_seconds']}s" if run.get("duration_seconds") is not None else "-"
        first_err = run["errors"][0] if run.get("errors") else "-"
        
        table.add_row(
            str(run["id"]),
            run["started_at"],
            get_status_style(run["status"]),
            dur,
            str(run.get("items_scraped", 0)),
            str(run.get("items_inserted", 0)),
            str(run.get("items_updated", 0)),
            first_err
        )

    console.print(table)

    # If the last run failed, display its traceback
    last_run = runs[0]
    if last_run["status"] == "failed" and last_run.get("traceback"):
        console.print("\n[bold red]Latest Run Failure Traceback details:[/bold red]")
        console.print(Panel(last_run["traceback"], border_style="red", title="Traceback Info"))

def main():
    parser = argparse.ArgumentParser(description="AssamStudentHub Scrapers Platform — Observability Dashboard CLI")
    parser.add_argument(
        "--inspect", "-i",
        choices=list(SCRAPER_CONFIG.keys()),
        default=None,
        help="Inspect detailed historical run logs and errors for a specific scraper"
    )
    parser.add_argument(
        "--watch", "-w",
        action="store_true",
        help="Auto-refresh the dashboard display list every 10 seconds"
    )

    args = parser.parse_args()
    console = Console()

    if args.inspect:
        render_inspect(console, args.inspect)
    elif args.watch:
        import time
        try:
            while True:
                console.clear()
                render_dashboard(console)
                time.sleep(10)
        except KeyboardInterrupt:
            console.print("\n[bold yellow]Dashboard watch loop terminated.[/bold yellow]")
    else:
        render_dashboard(console)

if __name__ == "__main__":
    main()
